# Search and Indexing in Codex

Codex does **not** have built-in vector embeddings, RAG, or a vector database like Qdrant/Gemma. Instead, it uses **fast keyword-based search** (BM25) for codebase navigation and relies on the model's context window for "understanding".

## How Codex finds answers fast

### 1. **Fuzzy File Search (BM25)**
- **What**: Fast fuzzy matching over file names/paths in the workspace.
- **How**: Implemented in [`app-server/src/fuzzy_file_search.rs`](codex-rs/app-server/src/fuzzy_file_search.rs) using `codex-file-search` crate (ripgrep for traversal + nucleo-matcher for fuzzy).
- **Triggered**: `/search` slash command or model tool call (`fuzzy_file_search`).
- **Config**: No direct config; controlled by `tools` features.
- **Speed**: Sub-second for large repos (ignores `.gitignore`).
- **Syntax**: `fuzzy_file_search_session_start` + `update` + `stop`.

### 2. **Text Search (rg preference)**
- **What**: Model-prompted `rg` (ripgrep) for content search.
- **Prompt guidance**: Models are instructed to prefer `rg` for speed (see model prompts like [`gpt-5.2-codex_prompt.md`](codex-rs/core/gpt-5.2-codex_prompt.md:1)).
- **No built-in index**: Relies on external `rg`; falls back to `grep`.

### 3. **Context Management (no embeddings)**
- **Truncation/Compaction**: Token budget enforced via `tool_output_token_limit`, `model_auto_compact_token_limit`.
- **No semantic search**: Pure keyword (BM25) + model reasoning.

## Adding Embeddings/RAG (via MCP/Tools)
Codex has no native embedding index, but you can integrate via **MCP servers** or custom tools.

### MCP for Embeddings
Configure an MCP server with embedding/vector DB tools:
```toml
[mcp_servers.embedding-rag]
enabled = true
transport = { stdio = { command = "/path/to/rag-mcp-server" } }
```

Model can call your MCP tools for embedding/query/retrieve.

### Custom Tool for Qdrant/Gemma
Define a dynamic tool that:
1. Embeds query with Gemma.
2. Queries Qdrant.
3. Returns top-k chunks.

See `tools.dynamic_tools` for integration.

## Config Impact on Search Speed
- `project_doc_max_bytes`: Limits AGENTS.md ingestion.
- `tool_output_token_limit`: Caps tool responses (e.g. search results).
- `web_search`: `"live"` vs `"cached"` affects external search latency.

For large codebases, enable `rg` in PATH and use `/search` liberally.

See [`codex-file-search/README.md`](codex-rs/file-search/README.md) for fuzzy matcher details.