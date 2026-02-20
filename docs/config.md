# Configuration (`config.toml`)

Codex is primarily configured via a TOML file located under your Codex home directory.

- Default location: `~/.codex/config.toml`
- Override location by setting `CODEX_HOME` (then config is loaded from `$CODEX_HOME/config.toml`)

This document focuses on **how to think about the settings**, how **precedence** works, and the **most commonly used keys**.

For official, always-up-to-date reference docs, see:

- Basic configuration: https://developers.openai.com/codex/config-basic
- Advanced configuration: https://developers.openai.com/codex/config-advanced
- Full key reference: https://developers.openai.com/codex/config-reference

## JSON Schema (authoritative in-repo reference)

The generated JSON Schema for `config.toml` is committed at:

- `codex-rs/core/config.schema.json`

If you use an editor with TOML + JSON-schema support, you can point it at this file to get:

- Auto-complete
- Inline documentation
- Type validation

## Configuration precedence (what wins?)

Codex merges configuration from multiple “levels”. When the same setting is defined in more than one place, **higher precedence wins**.

Precedence (highest to lowest) is:

1. Explicit CLI flags for the setting (example: `--model ...`)
2. Profile settings (selected by `--profile ...` or by `profile = "..."` in `config.toml`)
3. Top-level keys in `config.toml`
4. Built-in defaults in code

This precedence is documented in code (and tested) in the config module.

## Common patterns

### Minimal example

```toml
# Pick a default model
model = "gpt-5.1-codex"

# Make the default behavior safe for local repos
approval_policy = "untrusted"
sandbox_mode = "read-only"
```

### Profiles (recommended)

Use profiles when you want to switch between coherent “bundles” of settings.

```toml
profile = "work"

[profiles.work]
model = "gpt-5.1-codex"
approval_policy = "untrusted"
sandbox_mode = "read-only"

[profiles.local_dev]
model = "gpt-5.1-codex"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
```

Then start Codex with:

```bash
codex --profile local_dev
```

### One-off overrides (`-c key=value`)

Many Codex front-ends accept `-c` to apply a one-off override at runtime (useful for CI or ad-hoc sessions).

Example:

```bash
codex -c suppress_cyber_safety_warning=true
```

## Core top-level keys

This section describes the most important keys you’re likely to set directly.

### `model`

Default model slug to use when the client does not explicitly request one.

```toml
model = "gpt-5.1-codex"
```

Related:

- `review_model`: model used for `/review` sessions.
- `model_reasoning_effort`: controls `reasoning.effort` (Responses API).
- `model_reasoning_summary`: controls `reasoning.summary`.
- `model_verbosity`: GPT-5 verbosity control (`text.verbosity`).

### `model_provider`

Selects which entry in `model_providers` should be used.

```toml
model_provider = "openai"
```

### `model_providers.<id>`

Defines model provider endpoints and auth wiring.

Typical fields include:

- `base_url` (example: `https://api.openai.com/v1`)
- `env_key` (example: `OPENAI_API_KEY`)
- `wire_api` (for example, `responses`)

Example:

```toml
[model_providers.openai]
name = "OpenAI"
base_url = "https://api.openai.com/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
```

### `approval_policy`

Controls *when* Codex asks you before executing commands.

Common values:

- `"untrusted"`: conservative; only allow a very small set of safe read-only commands without asking.
- `"on-request"`: model chooses when to ask.
- `"never"`: never ask (non-interactive style).

Example:

```toml
approval_policy = "untrusted"
```

### `sandbox_mode`

Controls *how* command execution is sandboxed.

Common values:

- `"read-only"`: disallow writes by default.
- `"workspace-write"`: allow writes under controlled conditions.

Example:

```toml
sandbox_mode = "read-only"
```

### `web_search`

Controls web search tool behavior:

- `"disabled"`
- `"cached"`
- `"live"`

Example:

```toml
web_search = "cached"
```

### `developer_instructions` and `model_instructions_file`

Two different concepts:

- `developer_instructions`: a developer message inserted into the prompt at runtime.
- `model_instructions_file`: replaces built-in model instructions from a file.

The latter is discouraged because it can degrade model performance.

### `notify`

Runs an external notification command after each completed **turn**.

```toml
notify = ["notify-send", "Codex"]
```

Codex appends a JSON payload argument when it runs the command.

### `log_dir`

Directory where Codex writes logs (default: `$CODEX_HOME/log`).

```toml
log_dir = "/abs/path/to/codex-logs"
```

### `history`

Controls whether/what is persisted in `~/.codex/history.jsonl`.

If you need privacy or ephemeral runs, look for:

- `ephemeral` (session does not persist)

### `mcp_servers` (tools via MCP)

You can configure MCP servers under `mcp_servers`.

Because MCP configuration has its own detailed shape, this doc intentionally stays high-level.
Use the official config reference for the latest MCP options:

- https://developers.openai.com/codex/config-reference

### `apps` (Connectors)

Settings under `[apps]` configure app/connector visibility.

In the UI:

- Use `$` in the composer to insert a connector.
- Use `/apps` to list apps.

## TUI settings (`[tui]`)

If you use the terminal UI, the `[tui]` table contains UI-specific behavior.

Common items include:

- Alternate screen behavior
- Notification preferences
- Status line configuration

## Notices (`[notice]`)

Codex stores “do not show again” flags for some UI prompts under the `[notice]` table.

Example behavior:

- Ctrl+C / Ctrl+D quitting uses a ~1 second double-press hint (`ctrl + c again to quit`).

## Suppressing warnings

Codex emits some warning messages as part of normal operation.

### `suppress_cyber_safety_warning`

To suppress the specific “high-risk cyber activity” model downgrade warning message (the one that links to https://chatgpt.com/cyber), set:

```toml
suppress_cyber_safety_warning = true
```

Important:

- This only hides the warning **message**.
- It does **not** change server-side routing, sandbox behavior, approvals, or model selection.
