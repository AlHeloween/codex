# `config.toml` cookbook

This cookbook is a set of practical “recipes” for configuring Codex via `config.toml`.

It is designed to complement the per-property reference in [`docs/config.toml-reference.md`](docs/config.toml-reference.md).

## Before you start: what Codex expects from a model provider

Codex’s provider integration is based on **OpenAI-compatible Responses API** semantics.

- The only supported `wire_api` value today is `responses` (see [`WireApi`](codex-rs/core/src/model_provider_info.rs:34)).
- `wire_api = "chat"` is explicitly rejected (see error path in [`WireApi::deserialize()`](codex-rs/core/src/model_provider_info.rs:43)).

Implication:

- You can integrate **Grok / DeepSeek / Groq / other providers** *if and only if* the endpoint you point Codex at is compatible with the **Responses** API surface (typically: accepts requests at a `/v1/responses`-style endpoint, with compatible request/response JSON).
- If a provider only supports `/v1/chat/completions`, it will not work without adding new support in code.

## Recipe: Add a custom provider (generic OpenAI-compatible Responses endpoint)

Use this template for any third-party provider that offers an OpenAI-compatible “responses” endpoint.

```toml
model_provider = "thirdparty"

[model_providers.thirdparty]
name = "Third-party provider"
base_url = "https://api.example.com/v1"
env_key = "THIRDPARTY_API_KEY"
wire_api = "responses"

# Optional tuning
request_max_retries = 4
stream_max_retries = 5
stream_idle_timeout_ms = 300000

# Optional headers
http_headers = { "X-Client" = "codex" }

# Optional headers sourced from env vars
env_http_headers = { "X-Org" = "THIRDPARTY_ORG" }
```

Notes:

- `env_key` is the environment variable Codex will read to get your API key (see [`ModelProviderInfo::api_key()`](codex-rs/core/src/model_provider_info.rs:177)).
- If `env_key` is set but missing/empty at runtime, Codex returns an error.
- Avoid `experimental_bearer_token` unless you are embedding Codex programmatically (it’s discouraged for security) (see field docs in [`ModelProviderInfo`](codex-rs/core/src/model_provider_info.rs:57)).

## Recipe: Add Grok / DeepSeek / Groq-style providers

These providers differ mostly by **base URL**, **API key env var**, and sometimes required headers/query params.

The cookbook cannot hardcode their exact endpoints because they change; instead, use the generic template above and fill in:

- `base_url`
- `env_key`
- optional `http_headers` / `query_params`

Example:

```toml
[model_providers.groq]
name = "Groq"
base_url = "https://YOUR_GROQ_OPENAI_COMPAT_BASE/v1"
env_key = "GROQ_API_KEY"
wire_api = "responses"
```

```toml
[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://YOUR_DEEPSEEK_OPENAI_COMPAT_BASE/v1"
env_key = "DEEPSEEK_API_KEY"
wire_api = "responses"
```

```toml
[model_providers.grok]
name = "Grok"
base_url = "https://YOUR_GROK_OPENAI_COMPAT_BASE/v1"
env_key = "GROK_API_KEY"
wire_api = "responses"
```

If your provider does **not** support a Responses-compatible endpoint, these configurations will fail.

## Recipe: Switch providers via profiles

Profiles let you switch “bundles” of settings quickly.

```toml
profile = "work"

[profiles.work]
model_provider = "openai"
model = "gpt-5.1-codex"
approval_policy = "untrusted"
sandbox_mode = "read-only"

[profiles.alt_provider]
model_provider = "thirdparty"
model = "some-model-on-that-provider"
approval_policy = "untrusted"
sandbox_mode = "read-only"
```

Then:

```bash
codex --profile alt_provider
```

Precedence reminder: CLI flags override profiles; profiles override top-level values (see precedence note in [`codex-rs/core/src/config/mod.rs`](codex-rs/core/src/config/mod.rs:4076)).

## Recipe: Use a proxy (override built-in OpenAI provider)

The built-in OpenAI provider reads `OPENAI_BASE_URL` at runtime (see [`ModelProviderInfo::create_openai_provider()`](codex-rs/core/src/model_provider_info.rs:218)).

This is the easiest way to point Codex at:

- an OpenAI-compatible proxy
- a local mock server
- an Azure-style gateway (if it exposes compatible endpoints)

Example (shell):

```bash
set OPENAI_BASE_URL=https://proxy.example.com/v1
codex
```

## Recipe: Azure-style deployments (query params)

Some deployments require query params such as `api-version`.

Codex supports `query_params` in provider configs (see field in [`ModelProviderInfo`](codex-rs/core/src/model_provider_info.rs:81)).

```toml
[model_providers.azure]
name = "Azure"
base_url = "https://YOUR_RESOURCE.openai.azure.com/openai"
env_key = "AZURE_OPENAI_API_KEY"
wire_api = "responses"
query_params = { api-version = "2025-04-01-preview" }
```

## Recipe: Local providers (Ollama / LM Studio)

Codex includes built-in provider IDs for local OSS providers (see [`built_in_model_providers()`](codex-rs/core/src/model_provider_info.rs:271)):

- `ollama`
- `lmstudio`

Example:

```toml
model_provider = "ollama"
model = "gpt-oss"
```

## Recipe: Control execution risk (approval + sandbox defaults)

Recommended safe defaults for local repos:

```toml
approval_policy = "untrusted"
sandbox_mode = "read-only"
```

## Recipe: Suppress only the cyber-safety downgrade warning message

To hide the specific “high-risk cyber activity” warning message (no behavior change), set:

```toml
suppress_cyber_safety_warning = true
```

This aligns with the schema description (see [`codex-rs/core/config.schema.json`](codex-rs/core/config.schema.json:1715)).

