# config.toml Reference

This is the **complete, authoritative reference** for all `config.toml` properties, extracted directly from the [`ConfigToml`](codex-rs/core/src/config/mod.rs:874) struct and its nested types in [`types.rs`](codex-rs/core/src/config/types.rs).

## Format Legend
- **Name**: Property name.
- **Description**: Purpose and behavior (from source doc comments and schema).
- **Syntax**: TOML syntax example.
- **Type**: TOML type (with Rust equivalent).
- **Default**: Default value if omitted.
- **Notes**: Possible values, constraints, deprecations.

Properties are grouped by **namespace** (top-level or table), ordered as in `ConfigToml`.

## Top-Level Properties

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `model` | Optional override of model selection. Passed as `model` to Responses API. | `model = \"gpt-5.1-codex\"` | `string \| null` (`Option<String>`) | `null` | Model slug (e.g. \"gpt-5.1-codex\", \"o3\"). |
| `review_model` | Review model override used by the `/review` feature. | `review_model = \"gpt-4o-mini\"` | `string \| null` (`Option<String>`) | `null` | Model slug for review operations. |
| `model_provider` | Provider to use from the `model_providers` map. | `model_provider = \"openai\"` | `string \| null` (`Option<String>`) | `null` | Provider ID (e.g. \"openai\", \"openrouter\"). Defaults to \"openai\". |
| `model_context_window` | Size of the context window for the model, in tokens. | `model_context_window = 128000` | `integer \| null` (`Option<i64>`) | `null` | Overrides model's reported context window (≥0). |
| `model_auto_compact_token_limit` | Token usage threshold triggering auto-compaction of conversation history. | `model_auto_compact_token_limit = 80000` | `integer \| null` (`Option<i64>`) | `null` | Triggers history compaction when approaching limit (≥0). |
| `approval_policy` | Default approval policy for executing commands. | `approval_policy = \"untrusted\"` | `enum` (`Option<AskForApproval>`) | `null` | `untrusted`: Safe reads only. `on-failure`: Sandbox first (deprecated). `on-request`: Model decides. `never`: No approval. |
| `shell_environment_policy` | Policy for building `env` when spawning processes via shell tools. | `[shell_environment_policy]` | object (`ShellEnvironmentPolicyToml`) | `{}` | See [shell_environment_policy](#shell_environment_policy) section. |
| `sandbox_mode` | Sandbox mode to use for shell/unified exec. | `sandbox_mode = \"read-only\"` | `enum` (`Option<SandboxMode>`) | `null` | `read-only`: No writes. `workspace-write`: Controlled writes. `danger-full-access`: No sandbox. |
| `sandbox_workspace_write` | Sandbox configuration if `sandbox_mode = \"workspace-write\"`. | `[sandbox_workspace_write]` | object (`Option<SandboxWorkspaceWrite>`) | `null` | See [sandbox_workspace_write](#sandbox_workspace_write) section. |
| `notify` | Optional external command to spawn after each agent turn completes. | `notify = [\"notify-send\", \"Codex\"]` | `array<string> \| null` (`Option<Vec<String>>`) | `null` | Command + args; JSON payload appended as last arg. |
| `instructions` | Legacy system instructions (deprecated). | `instructions = \"...\"` | `string \| null` (`Option<String>`) | `null` | Use `model_instructions_file` or project AGENTS.md. |
| `developer_instructions` | Developer instructions inserted as a `developer` role message. | `developer_instructions = \"Think step-by-step\"` | `string \| null` (`Option<String>`) | `null` | Prepended to prompt. |
| `model_instructions_file` | Path to file overriding built-in model instructions. | `model_instructions_file = \"/path/to/instructions.txt\"` | `AbsolutePathBuf \| null` | `null` | **Strongly discouraged**; degrades performance. |
| `compact_prompt` | Custom prompt used for history compaction. | `compact_prompt = \"Summarize:\"` | `string \| null` (`Option<String>`) | `null` | Overrides built-in summarization. |
| `forced_chatgpt_workspace_id` | Restricts ChatGPT login to specific workspace ID. | `forced_chatgpt_workspace_id = \"ws-123\"` | `string \| null` | `null` | Trims whitespace; empty = no restriction. |
| `forced_login_method` | Restricts login mechanism. | `forced_login_method = \"chatgpt\"` | `enum \| null` (`Option<ForcedLoginMethod>`) | `null` | `chatgpt` \| `api`. |
| `cli_auth_credentials_store` | Backend for CLI auth credentials. | `cli_auth_credentials_store = \"keyring\"` | `enum` (`Option<AuthCredentialsStoreMode>`) | `auto` | `file`: `~/.codex/auth.json`. `keyring`: OS keyring. `auto`: Keyring if avail. `ephemeral`: Memory only. |
| `mcp_servers` | MCP servers for tool calls. | `[mcp_servers.example = { command = \"echo\" }]` | `HashMap<string, McpServerConfig>` | `{}` | See MCP docs. Filtered by requirements.toml. |
| `mcp_oauth_credentials_store` | Backend for MCP OAuth credentials. | `mcp_oauth_credentials_store = \"keyring\"` | `enum` (`Option<OAuthCredentialsStoreMode>`) | `auto` | `keyring`: OS keyring. `file`: `~/.codex/.credentials.json`. `auto`: Keyring if avail. |
| `mcp_oauth_callback_port` | Fixed port for MCP OAuth callback server. | `mcp_oauth_callback_port = 8080` | `u16 \| null` | `null` (ephemeral) | - |
| `model_providers` | User-defined model providers overriding built-ins. | `[model_providers.openai]` | `HashMap<string, ModelProviderInfo>` | `{}` | `base_url`, `env_key`, etc. |
| `project_doc_max_bytes` | Max bytes from AGENTS.md / project docs. | `project_doc_max_bytes = 8192` | `usize \| null` | 32768 | Silently truncates larger files. |
| `project_doc_fallback_filenames` | Fallback files if AGENTS.md missing. | `project_doc_fallback_filenames = [\"AGENTS.md\"]` | `array<string> \| null` | `[]` | Tried in order. |
| `tool_output_token_limit` | Token budget for tool outputs in context. | `tool_output_token_limit = 4096` | `usize \| null` | implementation default | Truncates longer outputs. |
| `js_repl_node_path` | Absolute path to Node for `js_repl` tool. | `js_repl_node_path = \"/usr/bin/node\"` | `AbsolutePathBuf \| null` | `null` (system node) | - |
| `profile` | Active profile from `profiles`. | `profile = \"work\"` | `string \| null` | `null` | Selects [profiles.work]. |
| `profiles` | Named config profiles. | `[profiles.work]` | `HashMap<string, ConfigProfile>` | `{}` | See [profiles](#profilesname). |
| `history` | History persistence settings. | `[history]` | `History \| null` | `{ persistence = \"save-all\" }` | See [history](#history). |
| `log_dir` | Log directory. | `log_dir = \"/path/to/logs\"` | `AbsolutePathBuf \| null` | `$CODEX_HOME/log` | e.g. codex-tui.log. |
| `file_opener` | URI scheme for file citations. | `file_opener = \"vscode\"` | `enum` (`Option<UriBasedFileOpener>`) | `vscode` | `vscode`, `vscode-insiders`, `windsurf`, `cursor`, `none`. |
| `tui` | TUI settings. | `[tui]` | `Tui \| null` | defaults | See [tui](#tui). |
| `hide_agent_reasoning` | Hide `AgentReasoning` events from UI. | `hide_agent_reasoning = true` | `bool` (`Option<bool>`) | `false` | Reduces noise. |
| `show_raw_agent_reasoning` | Show raw `AgentReasoningRawContentEvent`. | `show_raw_agent_reasoning = true` | `bool` (`Option<bool>`) | `false` | - |
| `model_reasoning_effort` | Responses API `reasoning.effort`. | `model_reasoning_effort = \"high\"` | `enum \| null` (`Option<ReasoningEffort>`) | `null` | `none`, `minimal`, `low`, `medium`, `high`, `xhigh`. |
| `model_reasoning_summary` | Responses API `reasoning.summary`. | `model_reasoning_summary = \"detailed\"` | `enum \| null` (`Option<ReasoningSummary>`) | `null` | `none`, `auto`, `concise`, `detailed`. |
| `model_supports_reasoning_summaries` | Force-enable reasoning summaries. | `model_supports_reasoning_summaries = true` | `bool \| null` | `null` | Overrides model info. |
| `model_verbosity` | GPT-5 `text.verbosity`. | `model_verbosity = \"high\"` | `enum \| null` (`Option<Verbosity>`) | `null` | `low`, `medium`, `high`. |
| `personality` | Model personality. | `personality = \"pragmatic\"` | `enum \| null` (`Option<Personality>`) | `null` | `none`, `friendly`, `pragmatic`. |
| `chatgpt_base_url` | ChatGPT backend URL. | `chatgpt_base_url = \"https://chatgpt.com/backend-api/\"` | `string` (`Option<String>`) | platform default | - |
| `projects` | Per-project overrides (trust levels). | `[projects]` | `HashMap<string, ProjectConfig>` | `{}` | Keyed by abs path. See [projects](#projects). |
| `web_search` | Web search mode. | `web_search = \"cached\"` | `enum` (`Option<WebSearchMode>`) | `null` (features-derived) | `disabled`, `cached`, `live`. |
| `tools` | Legacy tool toggles. | `[tools]` | `ToolsToml \| null` | defaults | `web_search`, `view_image`. Prefer `features`. |
| `agents` | Agent limits. | `[agents]` | `AgentsToml \| null` | defaults | See [agents](#agents). |
| `memories` | Memories subsystem. | `[memories]` | `MemoriesToml \| null` | defaults | See [memories](#memories). |
| `skills` | Per-skill configs. | `[skills]` | `SkillsConfig \| null` | `{}` | See [skills](#skills). |
| `features` | Feature flags. | `[features]` | `FeaturesToml` | platform defaults | See [features table](#features) below. |
| `suppress_unstable_features_warning` | Hide unstable feature warnings. | `suppress_unstable_features_warning = true` | `bool` | `false` | - |
| `suppress_cyber_safety_warning` | Hide cyber safety model warning. | `suppress_cyber_safety_warning = true` | `bool` | `false` | Message only. |
| `ghost_snapshot` | Undo snapshot settings. | `[ghost_snapshot]` | `GhostSnapshotToml \| null` | defaults | See [ghost_snapshot](#ghost_snapshot). |
| `project_root_markers` | Markers for project root detection. | `project_root_markers = [\".git\"]` | `array<string> \| null` | `[\".git\"]` | For `.codex` lookup. |
| `check_for_update_on_startup` | Enable update checks. | `check_for_update_on_startup = false` | `bool` | `true` | Disables prompts. |
| `disable_paste_burst` | Disable paste burst detection. | `disable_paste_burst = true` | `bool` | `false` | No input buffering. |
| `analytics` | Analytics toggle. | `[analytics]` | `AnalyticsConfigToml \| null` | `{ enabled = true }` | See [analytics](#analytics). |
| `feedback` | Feedback collection. | `[feedback]` | `FeedbackConfigToml \| null` | `{ enabled = true }` | See [feedback](#feedback). |
| `apps` | Per-app settings. | `[apps]` | `AppsConfigToml \| null` | `{}` | See [apps](#apps). |
| `otel` | OTEL exporters. | `[otel]` | `OtelConfigToml \| null` | defaults | See [otel](#otel). |
| `windows` | Windows-specific. | `[windows]` | `WindowsToml \| null` | `{}` | See [windows](#windows). |
| `windows_wsl_setup_acknowledged` | Dismiss WSL onboarding. | `windows_wsl_setup_acknowledged = true` | `bool` | `false` | Hides prompt. |
| `notice` | \"Do not show again\" flags. | `[notice]` | `Notice \| null` | `{}` | See [notice](#notice). |
| `experimental_instructions_file` | **Deprecated**: Ignored. | `experimental_instructions_file = \"/path\"` | `AbsolutePathBuf \| null` | `null` | Use `model_instructions_file`. |
| `experimental_compact_prompt_file` | **Deprecated**: Use `compact_prompt`. | `experimental_compact_prompt_file = \"/path\"` | `AbsolutePathBuf \| null` | `null` | - |
| `experimental_use_unified_exec_tool` | **Deprecated**: Use `features.unified_exec`. | `experimental_use_unified_exec_tool = true` | `bool` | `null` | - |
| `oss_provider` | Preferred OSS/local model provider. | `oss_provider = \"lmstudio\"` | `string \| null` | `null` | `lmstudio`, `ollama`. |

## Nested Tables

### [profiles.<name>]
Named config bundle (subset of top-level fields).

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| See top-level fields like `model`, `approval_policy`, etc. | Subset of `ConfigToml` fields. | `[profiles.work.model = \"o3\"]` | `ConfigProfile` | `{}` | Selected by `profile = \"work\"`. Full list in schema. |

### [model_providers.<id>]
Provider definition.

| Name | Description | Syntax | Type | Notes |
|-----|-------------|--------|------|-------|
| `base_url` | API base URL. | `base_url = \"https://api.example.com/v1\"` | `string` | Required. |
| `env_key` | Env var for API key. | `env_key = \"MY_API_KEY\"` | `string` | Preferred over `experimental_bearer_token`. |
| `name` | Display name. | `name = \"My Provider\"` | `string` | Required. |
| Others | `http_headers`, `env_http_headers`, `wire_api = \"responses\"`, etc. | - | See [`ModelProviderInfo`](codex-rs/core/src/model_provider_info.rs) | - |

### [shell_environment_policy]
Policy for shell `env`.

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `inherit` | Starting env vars. | `inherit = \"core\"` | `enum` (`Option<ShellEnvironmentPolicyInherit>`) | `all` | `core`, `all`, `none`. |
| `ignore_default_excludes` | Skip default excludes (KEY/SECRET/TOKEN). | `ignore_default_excludes = false` | `bool` | `true` | - |
| `exclude` | Regex patterns to exclude. | `exclude = [\"SECRET.*\"]` | `array<string>` | `[]` | Case-insensitive wildmatch. |
| `set` | Explicit vars to set. | `set = { FOO = \"bar\" }` | `object` | `{}` | Overrides. |
| `include_only` | Whitelist after excludes. | `include_only = [\"PATH\"]` | `array<string>` | `[]` | Case-insensitive wildmatch. |
| `experimental_use_profile` | Use shell profile. | `experimental_use_profile = true` | `bool` | `false` | - |

### [sandbox_workspace_write]
Extra config for `sandbox_mode = \"workspace-write\"`.

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `writable_roots` | Additional writable absolute paths. | `writable_roots = [\"/tmp\"]` | `array<AbsolutePathBuf>` | `[]` | Beyond workspace root. |
| `network_access` | Allow network in sandbox. | `network_access = true` | `bool` | `false` | - |
| `exclude_tmpdir_env_var` | Exclude `$TMPDIR`. | `exclude_tmpdir_env_var = true` | `bool` | `false` | - |
| `exclude_slash_tmp` | Exclude `/tmp`. | `exclude_slash_tmp = true` | `bool` | `false` | - |

### [tui]
TUI settings.

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `alternate_screen` | Alternate screen buffer. | `alternate_screen = \"auto\"` | `enum` (`AltScreenMode`) | `auto` | `auto`: Detect Zellij. `always`, `never`. |
| `notifications` | Triggers for notifications. | `notifications = [\"approval\", \"turn_complete\"]` | `array<string> \| bool` (`Notifications`) | `true` | bool=true enables all. |
| `notification_method` | Method for notifications. | `notification_method = \"osc9\"` | `enum` (`NotificationMethod`) | `auto` | `auto`, `osc9`, `bel`. |
| `animations` | Enable animations/shimmers. | `animations = false` | `bool` | `true` | - |
| `show_tooltips` | Welcome screen tooltips. | `show_tooltips = false` | `bool` | `true` | - |
| `experimental_mode` | Initial mode. | `experimental_mode = \"plan\"` | `enum` (`Option<ModeKind>`) | `null` | `plan`, `default`. |
| `status_line` | Status items order. | `status_line = [\"model\", \"mode\"]` | `array<string>` | `null` (default order) | - |

### [history]
History.jsonl settings.

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `persistence` | Save to disk? | `persistence = \"none\"` | `enum` (`HistoryPersistence`) | `save-all` | `save-all`, `none`. |
| `max_bytes` | Max file size (drop oldest). | `max_bytes = 1048576` | `usize` | unlimited | - |

### [agents]
| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `max_threads` | Max concurrent threads. | `max_threads = 4` | `usize` (≥1) | 6 | 0 invalid. |

### [memories]
| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `max_raw_memories_for_global` | Max recent raw memories. | `max_raw_memories_for_global = 512` | `usize` | 1024 | ≤4096. |
| `max_rollout_age_days` | Max thread age. | `max_rollout_age_days = 30` | `i64` | 30 | 0-90. |
| `max_rollouts_per_startup` | Max rollouts per pass. | `max_rollouts_per_startup = 8` | `usize` | 8 | ≤128. |
| `min_rollout_idle_hours` | Min idle before rollout. | `min_rollout_idle_hours = 12` | `i64` | 12 | 1-48h. |
| `phase_1_model` | Thread summarization model. | `phase_1_model = \"gpt-4o-mini\"` | `string` | null | - |
| `phase_2_model` | Consolidation model. | `phase_2_model = \"gpt-4o-mini\"` | `string` | null | - |

### [skills]
Per-skill overrides.

| Name | Description | Syntax | Type | Notes |
|-----|-------------|--------|------|-------|
| `<skill path>` | Skill config. | `[skills.SKILL.md.enabled = false]` | object (`SkillConfig`) | `enabled: bool`, `path: AbsolutePathBuf`. |

### [apps]
Per-app settings.

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `<app-id>` | App config. | `[apps.chatgpt.enabled = false]` | `AppConfig` | `{enabled=true}` | `disabled_reason: enum (unknown/user)`. |

### [analytics]
| Name | Description | Syntax | Type | Default |
|-----|-------------|--------|------|---------|
| `enabled` | Disable analytics. | `enabled = false` | `bool` | `true` |

### [feedback]
| Name | Description | Syntax | Type | Default |
|-----|-------------|--------|------|---------|
| `enabled` | Disable feedback. | `enabled = false` | `bool` | `true` |

### [otel]
OTEL exporters.

| Name | Description | Syntax | Type | Default | Notes |
|-----|-------------|--------|------|---------|-------|
| `log_user_prompt` | Log prompts in traces. | `log_user_prompt = true` | `bool` | `false` | - |
| `environment` | Trace env tag. | `environment = \"prod\"` | `string` | \"dev\" | - |
| `exporter` / `trace_exporter` / `metrics_exporter` | Exporter kind. | `exporter = { otlp-http.endpoint = \"...\" }` | `OtelExporterKind` | `none` / `none` / `statsig` | `none`, `statsig`, `otlp-http`, `otlp-grpc`. |

### [windows]
| Name | Description | Syntax | Type | Default |
|-----|-------------|--------|------|---------|
| `sandbox` | Windows sandbox level. | `sandbox = \"unelevated\"` | `enum` (`WindowsSandboxModeToml`) | `null` (features) | `elevated`, `unelevated`. |

### [notice]
\"Do not show again\" flags.

| Name | Description | Syntax | Type |
|-----|-------------|--------|------|
| `hide_full_access_warning` | Dismiss full access warning. | `hide_full_access_warning = true` | `bool` |
| `hide_world_writable_warning` | Dismiss world-writable warning. | `hide_world_writable_warning = true` | `bool` |
| `hide_rate_limit_model_nudge` | Dismiss rate limit nudge. | `hide_rate_limit_model_nudge = true` | `bool` |
| `hide_gpt5_1_migration_prompt` | Dismiss GPT-5.1 migration. | `hide_gpt5_1_migration_prompt = true` | `bool` |
| `hide_gpt-5.1-codex-max_migration_prompt` | Dismiss gpt-5.1-codex-max migration. | `hide_gpt-5.1-codex-max_migration_prompt = true` | `bool` |
| `model_migrations` | Acknowledged migrations (old=new). | `model_migrations.old = \"new\"` | `object<string,string>` |

### [ghost_snapshot]
Undo settings.

| Name | Description | Syntax | Type | Default |
|-----|-------------|--------|------|---------|
| `ignore_large_untracked_files` | Exclude large untracked files (>bytes). | `ignore_large_untracked_files = 1048576` | `i64` | null |
| `ignore_large_untracked_dirs` | Ignore large untracked dirs (≥files). | `ignore_large_untracked_dirs = 1000` | `i64` | null |
| `disable_warnings` | Disable warnings. | `disable_warnings = true` | `bool` | false |

## Features Table
Known flags from [`FEATURES`](codex-rs/core/src/features.rs).

| Key | Feature | Stage | Default | Description |
|-----|---------|-------|---------|-------------|
| `undo` | GhostCommit | Stable | false | Undo via ghost commits. |
| `shell_tool` | ShellTool | Stable | true | Default shell tool. |
| `js_repl` | JsRepl | UnderDevelopment | false | JS REPL. |
| `js_repl_tools_only` | JsReplToolsOnly | UnderDevelopment | false | JS REPL tools only. |
| `unified_exec` | UnifiedExec | Stable | !windows | Unified PTY exec. |
| `apply_patch_freeform` | ApplyPatchFreeform | UnderDevelopment | false | Freeform `apply_patch`. |
| `web_search_request` | WebSearchRequest | Deprecated | false | Live search (use `web_search = \"live\"`). |
| `web_search_cached` | WebSearchCached | Deprecated | false | Cached search (use `web_search = \"cached\"`). |
| `search_tool` | SearchTool | Removed | false | Legacy. |
| `runtime_metrics` | RuntimeMetrics | UnderDevelopment | false | Metrics snapshots. |
| `sqlite` | Sqlite | UnderDevelopment | false | SQLite rollout metadata. |
| `memory_tool` | MemoryTool | UnderDevelopment | false | Memory extraction. |
| `child_agents_md` | ChildAgentsMd | UnderDevelopment | false | AGENTS.md guidance. |
| `use_linux_sandbox_bwrap` | UseLinuxSandboxBwrap | Experimental (Linux) | false | Bubblewrap. |
| `request_rule` | RequestRule | Removed | false | - |
| `experimental_windows_sandbox` | WindowsSandbox | Removed | false | - |
| `elevated_windows_sandbox` | WindowsSandboxElevated | Removed | false | - |
| `remote_models` | RemoteModels | Stable | true | Remote model refresh. |
| `powershell_utf8` | PowershellUtf8 | Stable (Windows) | true | UTF-8 PowerShell. |
| `enable_request_compression` | EnableRequestCompression | Stable | true | Compress requests. |
| `multi_agent` / `collab` | Collab | Experimental | false | Multi-agent. |
| `apps` | Apps | Experimental | false | ChatGPT Apps. |
| `apps_mcp_gateway` | AppsMcpGateway | UnderDevelopment | false | Apps MCP gateway. |
| `skill_mcp_dependency_install` | SkillMcpDependencyInstall | Stable | true | MCP deps install. |
| `skill_env_var_dependency_prompt` | SkillEnvVarDependencyPrompt | UnderDevelopment | false | Skill env prompt. |
| `steer` | Steer | Stable | true | Steer mode (Enter=submit). |
| `collaboration_modes` | CollaborationModes | Stable | true | Plan/Default modes. |
| `personality` | Personality | Stable | true | Personality selection. |
| `prevent_idle_sleep` | PreventIdleSleep | Experimental (macOS) | false | Prevent sleep during turns. |
| `responses_websockets` | ResponsesWebsockets | UnderDevelopment | false | WS transport. |
| `responses_websockets_v2` | ResponsesWebsocketsV2 | UnderDevelopment | false | WS v2. |

Unknown keys warn.

## CLI Overrides (`-c`)
Runtime overrides (`-c key=value`), highest precedence.

Examples:
- `-c model=gpt-5.1-codex`
- `-c tui.alternate_screen=never`
- `-c suppress_cyber_safety_warning=true`
- `-c profile=work`

Nested supported (dot notation).