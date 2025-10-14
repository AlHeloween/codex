#!/usr/bin/env python3
"""Codex MCP proxy with auto-restart, logging, and wxPython GUI hints.

This example bridges the stdio-based `codex mcp` server to an HTTP/SSE
interface that tools such as GitHub's "Git Code" assistant can consume.
It demonstrates:

- supervised subprocess restarts when `codex mcp` exits unexpectedly
- structured logging to both a rotating log file and a GUI console
- a lightweight wxPython control panel with connection hints and status

The transport exposed by this proxy follows the Model Context Protocol's
legacy HTTP + Server Sent Events conventions:

    POST /messages   → forward JSON-RPC payloads to Codex
    GET  /sse        → stream JSON-RPC responses as SSE `message` events
    GET  /ready      → health endpoint reporting Codex status

Run the proxy, then point your MCP-compatible client at the configured
host/port (default: http://127.0.0.1:8765).

Requires: aiohttp, wxPython.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import os
import queue
import shlex
import signal
import sys
import threading
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from collections import deque
from typing import Any, Dict, List, Optional, Set

from aiohttp import web

try:
    import wx  # type: ignore
except ImportError as exc:  # pragma: no cover - GUI import guard
    raise SystemExit(
        "wxPython is required for this example. Install it with `pip install wxPython`."
    ) from exc


DEFAULT_CMD = os.environ.get("CODEX_CMD", "codex mcp")
DEFAULT_HOST = os.environ.get("MCP_PROXY_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("MCP_PROXY_PORT", "8765"))
DEFAULT_RESTART_DELAY = float(os.environ.get("MCP_PROXY_RESTART_DELAY", "3.0"))
DEFAULT_LOG_PATH = Path(os.environ.get("MCP_PROXY_LOG", "codex_mcp_proxy.log")).resolve()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cmd",
        default=DEFAULT_CMD,
        help="Command used to launch the Codex MCP server (default: %(default)s)",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="HTTP bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP bind port")
    parser.add_argument(
        "--restart-delay",
        type=float,
        default=DEFAULT_RESTART_DELAY,
        help="Delay before restarting Codex after an unexpected exit (seconds)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="Path to the rotating log file (default: %(default)s)",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without the wxPython control panel (headless mode)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        type=str.upper,
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Minimum log level for proxy logs (default: %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Shortcut for --log-level DEBUG",
    )
    return parser.parse_args(argv)


class AsyncRuntime:
    """Owns an asyncio loop running on a dedicated daemon thread."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="async-runtime", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit(self, coro: Any) -> asyncio.Future:
        """Schedule *coro* on the loop, return a concurrent Future."""

        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def shutdown(self) -> None:
        def stop_loop() -> None:
            self.loop.stop()

        self.loop.call_soon_threadsafe(stop_loop)
        self._thread.join(timeout=2)


class BroadcastHub:
    """Tracks SSE subscribers, forwards events, and replays recent history."""

    def __init__(self, history_size: int = 32) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._history: deque[Dict[str, Any]] = deque(maxlen=history_size)

    def subscribe(self) -> asyncio.Queue:
        queue_: asyncio.Queue = asyncio.Queue(maxsize=200)
        for event in list(self._history):
            queue_.put_nowait(event)
        self._subscribers.add(queue_)
        return queue_

    def unsubscribe(self, queue_: asyncio.Queue) -> None:
        self._subscribers.discard(queue_)

    async def publish(self, event: Dict[str, Any]) -> None:
        if "event" not in event:
            raise ValueError("Broadcast event must include an 'event' key")
        self._history.append(event)
        stale: List[asyncio.Queue] = []
        for subscriber in list(self._subscribers):
            while subscriber.full():
                try:
                    subscriber.get_nowait()
                except asyncio.QueueEmpty:
                    break
            try:
                subscriber.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(subscriber)
        for subscriber in stale:
            self._subscribers.discard(subscriber)


@dataclass
class SupervisorEvent:
    type: str
    payload: Dict[str, Any]


class CodexProcessSupervisor:
    """Launches and supervises the `codex mcp` process with restarts."""

    def __init__(
        self,
        command: str,
        restart_delay: float,
        broadcast: BroadcastHub,
        status_queue: "queue.Queue[SupervisorEvent]",
        logger: logging.Logger,
    ) -> None:
        self.command = command
        self.restart_delay = restart_delay
        self.broadcast = broadcast
        self.status_queue = status_queue
        self.logger = logger
        self._keep_running = asyncio.Event()
        self._run_task: Optional[asyncio.Task] = None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._stdin_lock = asyncio.Lock()
        self._state = "stopped"

    @property
    def state(self) -> str:
        return self._state

    async def start(self) -> None:
        if self._run_task and not self._run_task.done():
            self.logger.debug("Supervisor already running")
            return
        self.logger.info("Starting Codex MCP supervisor")
        self._keep_running.set()
        self._run_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if not self._keep_running.is_set():
            return
        self.logger.info("Stopping Codex MCP supervisor")
        self._keep_running.clear()
        if self._proc and self._proc.returncode is None:
            self.logger.debug("Terminating codex mcp (PID %s)", self._proc.pid)
            with contextlib.suppress(ProcessLookupError):
                self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.logger.warning("codex mcp unresponsive; killing")
                with contextlib.suppress(ProcessLookupError):
                    self._proc.kill()
                await asyncio.wait_for(self._proc.wait(), timeout=3)
        if self._run_task:
            await self._run_task
        self._proc = None
        self._run_task = None
        await self._set_state("stopped", "Supervisor stopped")

    async def ensure_process(self) -> None:
        if self._proc and self._proc.returncode is None:
            self.logger.info("Restart requested while process is running")
            with contextlib.suppress(RuntimeError):
                await self._terminate_proc()
        if not self._keep_running.is_set():
            self._keep_running.set()
            self._run_task = asyncio.create_task(self._run_loop())

    async def send_json(self, payload: Dict[str, Any]) -> None:
        if not self._proc or self._proc.returncode is not None or not self._proc.stdin:
            raise RuntimeError("codex mcp is not running")
        data = json.dumps(payload)
        async with self._stdin_lock:
            self.logger.debug("→ Codex: %s", data)
            self._proc.stdin.write(data.encode("utf-8") + b"\n")
            await self._proc.stdin.drain()

    async def _run_loop(self) -> None:
        while self._keep_running.is_set():
            await self._launch_proc()
            if not self._proc:
                await self._set_state("error", "Failed to launch codex mcp")
                await asyncio.sleep(self.restart_delay)
                continue

            return_code = await self._proc.wait()
            self.logger.warning("codex mcp exited with code %s", return_code)
            await self.broadcast.publish(
                {"event": "status", "data": {"state": "exited", "returnCode": return_code}}
            )
            await self._set_state("exited", f"codex mcp exited with code {return_code}")
            if not self._keep_running.is_set():
                break
            await asyncio.sleep(self.restart_delay)
            await self._set_state("restarting", "Restarting codex mcp")
        self.logger.debug("Supervisor loop exiting")

    async def _launch_proc(self) -> None:
        tokens = shlex.split(self.command, posix=(os.name != "nt"))
        cmd_display = " ".join(tokens)
        self.logger.info("Launching `%s`", cmd_display)
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *tokens,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            self.logger.exception("Failed to spawn `%s`", cmd_display)
            self._proc = None
            await self._set_state("error", f"Command not found: {tokens[0]}")
            return

        await self._set_state("running", f"codex mcp running (PID {self._proc.pid})")
        asyncio.create_task(self._pump_stream(self._proc.stdout, is_stdout=True))
        asyncio.create_task(self._pump_stream(self._proc.stderr, is_stdout=False))

    async def _pump_stream(
        self,
        stream: Optional[asyncio.StreamReader],
        *,
        is_stdout: bool,
    ) -> None:
        if not stream:
            return
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if is_stdout:
                await self.broadcast.publish({"event": "message", "data": text})
                self.logger.info("stdout: %s", text)
            else:
                await self.broadcast.publish({"event": "stderr", "data": text})
                self.logger.warning("stderr: %s", text)

    async def _set_state(self, state: str, message: str) -> None:
        self._state = state
        event = SupervisorEvent("state", {"state": state, "message": message})
        self.status_queue.put(event)
        await self.broadcast.publish(
            {"event": "status", "data": {"state": state, "message": message}}
        )

    async def _terminate_proc(self) -> None:
        if not self._proc:
            raise RuntimeError("Process not running")
        with contextlib.suppress(ProcessLookupError):
            self._proc.terminate()
        await asyncio.wait_for(self._proc.wait(), timeout=3)


class ProxyService:
    """Combines the supervisor with aiohttp endpoints."""

    def __init__(self, supervisor: CodexProcessSupervisor, logger: logging.Logger) -> None:
        self.supervisor = supervisor
        self.logger = logger
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.BaseSite] = None

    def _create_app(self) -> web.Application:
        app = web.Application()
        app["supervisor"] = self.supervisor

        async def ready_handler(request: web.Request) -> web.Response:
            sup: CodexProcessSupervisor = request.app["supervisor"]
            return web.json_response({"status": sup.state})

        async def messages_handler(request: web.Request) -> web.Response:
            raw_body = await request.text()
            self.logger.debug("<- HTTP %s %s: %s", request.method, request.path, raw_body)
            if not raw_body:
                return web.json_response(
                    {"error": "empty-body", "message": "Expected JSON-RPC payload"},
                    status=400,
                )
            sup: CodexProcessSupervisor = request.app["supervisor"]
            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError as err:
                self.logger.warning("Bad JSON payload: %s", err)
                return web.json_response({"error": "invalid-json", "message": str(err)}, status=400)
            try:
                await sup.send_json(payload)
            except RuntimeError as err:
                self.logger.error("Dropping message; codex not running: %s", err)
                return web.json_response({"error": "not-ready", "message": str(err)}, status=503)
            return web.Response(status=202)

        async def sse_handler(request: web.Request) -> web.StreamResponse:
            sup: CodexProcessSupervisor = request.app["supervisor"]
            queue_ = sup.broadcast.subscribe()
            self.logger.debug("<- SSE connect %s %s headers=%s", request.method, request.path, dict(request.headers))
            response = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
            await response.prepare(request)
            prologue = request.headers.get("x-mcp-initial-request")
            if prologue:
                try:
                    self.logger.debug("<- SSE prologue: %s", prologue)
                    await sup.send_json(json.loads(prologue))
                except json.JSONDecodeError as err:
                    self.logger.warning("Bad x-mcp-initial-request header: %s", err)
            try:
                status_payload = json.dumps({"status": sup.state})
                await response.write(f"event: status\ndata: {status_payload}\n\n".encode("utf-8"))
                while True:
                    event = await queue_.get()
                    event_name = event.get("event", "message")
                    data = event.get("data", "")
                    if not isinstance(data, str):
                        data = json.dumps(data)
                    await response.write(f"event: {event_name}\ndata: {data}\n\n".encode("utf-8"))
                    await response.drain()
            except (asyncio.CancelledError, ConnectionResetError):
                pass
            finally:
                sup.broadcast.unsubscribe(queue_)
            return response

        app.router.add_get("/ready", ready_handler)
        app.router.add_post("/messages", messages_handler)
        app.router.add_get("/sse", sse_handler)

        # VS Code's Git Code assistant probes the root path before falling back
        # to the legacy SSE endpoints. Treat this as a friendly alias so we
        # don't 404 during the initial handshake.
        app.router.add_post("/", messages_handler)
        app.router.add_get("/", sse_handler)
        return app

    async def start(self, host: str, port: int) -> None:
        await self.supervisor.start()
        app = self._create_app()
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host=host, port=port)
        await self.site.start()
        self.logger.info("HTTP proxy listening on http://%s:%s", host, port)

    async def stop(self) -> None:
        await self.supervisor.stop()
        if self.site:
            await self.site.stop()
            self.site = None
        if self.runner:
            await self.runner.cleanup()
            self.runner = None


class QueueLogHandler(logging.Handler):
    """Push log records onto a standard queue for the GUI."""

    def __init__(self, target_queue: "queue.Queue[SupervisorEvent]") -> None:
        super().__init__()
        self.target_queue = target_queue

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        event = SupervisorEvent("log", {"message": msg})
        try:
            self.target_queue.put_nowait(event)
        except queue.Full:  # pragma: no cover - queue is unbounded by default
            pass


class ProxyFrame(wx.Frame):
    """wxPython control panel showing status, log tail, and connection hints."""

    def __init__(
        self,
        runtime: AsyncRuntime,
        service: ProxyService,
        status_queue: "queue.Queue[SupervisorEvent]",
        host: str,
        port: int,
    ) -> None:
        super().__init__(parent=None, title="Codex MCP Proxy", size=(740, 540))
        self.runtime = runtime
        self.service = service
        self.status_queue = status_queue
        self.host = host
        self.port = port
        self.log_lines: List[str] = []

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.status_label = wx.StaticText(panel, label="Status: starting…")
        font = self.status_label.GetFont()
        font.MakeBold()
        self.status_label.SetFont(font)
        sizer.Add(self.status_label, flag=wx.ALL, border=8)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.restart_button = wx.Button(panel, label="Restart Codex")
        self.stop_button = wx.Button(panel, label="Stop Codex")
        button_sizer.Add(self.restart_button, flag=wx.ALL, border=5)
        button_sizer.Add(self.stop_button, flag=wx.ALL, border=5)
        sizer.Add(button_sizer, flag=wx.ALL, border=5)

        self.log_ctrl = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
            size=(-1, 240),
        )
        sizer.Add(self.log_ctrl, flag=wx.ALL | wx.EXPAND, border=8, proportion=1)

        tips = (
            "Git Code setup hints:\n"
            "  1. Enable MCP experimental features in VS Code settings.\n"
            "  2. Add a custom MCP server pointing to http://{host}:{port}.\n"
            "  3. Set the transport to HTTP/SSE (legacy).\n"
            "  4. Restart Git Code to pick up changes."
        ).format(host=host, port=port)
        self.hint_ctrl = wx.StaticText(panel, label=tips)
        sizer.Add(self.hint_ctrl, flag=wx.ALL, border=8)

        panel.SetSizer(sizer)

        self.restart_button.Bind(wx.EVT_BUTTON, self.on_restart)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(250)

    def on_restart(self, _: wx.CommandEvent) -> None:
        future = self.runtime.submit(self.service.supervisor.ensure_process())
        future.add_done_callback(lambda f: f.exception())

    def on_stop(self, _: wx.CommandEvent) -> None:
        future = self.runtime.submit(self.service.supervisor.stop())
        future.add_done_callback(lambda f: f.exception())

    def on_close(self, event: wx.CloseEvent) -> None:
        self.timer.Stop()
        future = self.runtime.submit(self.service.stop())
        future.result(timeout=10)
        self.runtime.shutdown()
        event.Skip()

    def on_timer(self, _: wx.TimerEvent) -> None:
        while True:
            try:
                event = self.status_queue.get_nowait()
            except queue.Empty:
                break
            if event.type == "state":
                state = event.payload.get("state", "unknown")
                message = event.payload.get("message", "")
                self.status_label.SetLabel(f"Status: {state} — {message}")
            elif event.type == "log":
                self._append_log_line(event.payload.get("message", ""))

    def _append_log_line(self, message: str) -> None:
        if not message:
            return
        self.log_lines.append(message)
        if len(self.log_lines) > 500:
            self.log_lines = self.log_lines[-500:]
        self.log_ctrl.SetValue("\n".join(self.log_lines))
        self.log_ctrl.ShowPosition(self.log_ctrl.GetLastPosition())


def configure_logging(
    log_path: Path,
    status_queue: "queue.Queue[SupervisorEvent]",
    log_level: str,
) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("codex_mcp_proxy")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    queue_handler = QueueLogHandler(status_queue)
    queue_handler.setFormatter(formatter)
    queue_handler.setLevel(level)
    logger.addHandler(queue_handler)

    return logger


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    status_queue: "queue.Queue[SupervisorEvent]" = queue.Queue()
    log_level = "DEBUG" if args.verbose else args.log_level
    logger = configure_logging(args.log_file, status_queue, log_level)

    broadcast = BroadcastHub()
    supervisor = CodexProcessSupervisor(
        command=args.cmd,
        restart_delay=args.restart_delay,
        broadcast=broadcast,
        status_queue=status_queue,
        logger=logger,
    )
    service = ProxyService(supervisor, logger)

    runtime = AsyncRuntime()
    runtime.start()

    start_future = runtime.submit(service.start(args.host, args.port))
    start_future.result()

    if args.no_gui:
        logger.info(
            "Headless mode active. Press Ctrl+C to stop. HTTP endpoint at http://%s:%s",
            args.host,
            args.port,
        )
        try:
            while True:
                signal.pause()
        except AttributeError:
            # Windows: signal.pause unavailable
            try:
                while True:
                    threading.Event().wait(timeout=3600)
            except KeyboardInterrupt:
                pass
        except KeyboardInterrupt:
            pass
        finally:
            stop_future = runtime.submit(service.stop())
            stop_future.result()
            runtime.shutdown()
        return

    app = wx.App()
    frame = ProxyFrame(runtime, service, status_queue, args.host, args.port)
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
