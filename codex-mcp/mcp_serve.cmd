@echo off
REM mcp_serve.cmd - helper to launch Codex in MCP server mode.
REM
REM This script forwards any additional arguments to `codex mcp serve` and
REM points Codex at the sibling `mcp_serve_config.toml` so you can tweak
REM sandbox or profile settings without touching your global config.

setlocal ENABLEEXTENSIONS

REM Resolve the directory that contains this script.
set SCRIPT_DIR=%~dp0

REM Canonical path to the optional per-script config.
set CONFIG_FILE=%SCRIPT_DIR%mcp_serve_config.toml

REM Allow callers to override the codex binary via CODex_BIN, otherwise rely on PATH.
if not defined CODEX_BIN set CODEX_BIN=codex.exe

echo Launching Codex MCP server...
"%CODEX_BIN%" --config "%CONFIG_FILE%" mcp serve %*

endlocal
