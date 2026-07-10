# Plan: Upstream Merge (July 2026)

## Goal
Merge `upstream/main` (openai/codex) into `Local_Mod`, preserving all 14 local features and customizations.

## Current State
- **Branch**: `Local_Mod` (tracking `origin/Local_Mod` on `AlHeloween/codex`)
- **Upstream**: `openai/codex` main (30 commits ahead, ~2600 files changed)
- **Last merge**: `d0e7f625cd` (then 2 more local commits on top)
- **Local commits on top of upstream**: 14 non-merge commits (early ones were squashed merges, later ones are feature work)

## Local Features to Preserve

### A. Core Code Changes (will conflict — need manual resolution)
| # | Feature | Files | Nature |
|---|---------|-------|--------|
| A1 | `suppress_cyber_safety_warning` config | `config_toml.rs`, `config/mod.rs`, `codex_thread.rs` | Adds config field to suppress "high-risk cyber activity" model downgrade warning |
| A2 | `active_profile` tracking | `config/mod.rs` | Tracks which profile name derived the Config |
| A3 | `ServiceTier` type change | `codex_thread.rs` | `service_tier` changed from `Option<String>` to `Option<ServiceTier>` |
| A4 | Cargo profile customizations | `Cargo.toml` | version=0.300.0, lto=false, debug=0 in release, codegen-units=1 in dev |

### B. Config/Infra (no conflicts expected)
| # | Feature | Files |
|---|---------|-------|
| B1 | Custom .gitignore rules | `.gitignore` (ignore `*/target/*`, `.opencode/`, `.adid_rag/`) |
| B2 | Fork sync workflow | `.github/workflows/sync-fork.yml` |
| B3 | Custom cargo config | `codex-rs/.cargo/config.toml` |
| B4 | adm.json (stop tracking) | `adm.json` — NOT yet in .gitignore; must add then `git rm --cached` |
| B5 | Config schema | `codex-rs/core/config.schema.json` — locally modified; regenerate after merge |

### C. Tests
| # | Feature | Files |
|---|---------|-------|
| C1 | User agent test | `codex-rs/app-server/tests/suite/user_agent.rs` (new file) |
| C2 | Safety check downgrade test | `codex-rs/core/tests/suite/safety_check_downgrade.rs` (modified) |
| C3 | v2 safety check test | `codex-rs/app-server/tests/suite/v2/safety_check_downgrade.rs` (modified) |

### D. Documentation & Diagrams
| # | Feature | Files |
|---|---------|-------|
| D1 | Custom docs | `docs/codex-config-cookbook.md`, `docs/codex-config-toml-ref.md`, `docs/config.md` (locally modified — preserves suppress_cyber_safety_warning docs), `docs/search-indexing.md` |
| D2 | Diagrams | `diagrams/codex_5.3_security.md`, `diagrams/cyber_error_flow.md` (empty), `diagrams/cyber_safety_error.md`, `diagrams/cyber_safety_message.md`, `diagrams/trust_levels.md` |

### E. Local Configs (not in upstream, won't conflict)
| # | Feature | Files |
|---|---------|-------|
| E1 | Gateway config | `.opencode/gateway.json` |
| E2 | MCP config | `.roo/mcp.json` |

## Merge Conflict Forecast

Based on diff analysis:

| File | Our changes | Upstream changes | Conflict Likelihood |
|------|------------|-------------------|---------------------|
| `core/src/config/mod.rs` | +5 lines (suppress_cyber, active_profile) | +1098 lines (major refactor) | **HIGH** — our additions land in heavily refactored sections |
| `codex_thread.rs` | +4 lines (import ServiceTier, add field) | +408 lines | **HIGH** — ThreadConfigSnapshot restructured |
| `config_toml.rs` | +3 lines (add field) | +68 lines, major restructuring | **HIGH** — upstream heavily restructured config; our field lands in a different context |
| `Cargo.toml` | Profile customizations | +93 lines (new crates, restructured profiles) | **MEDIUM** — profile sections overlap |
| `Cargo.lock` | Version bumps | +2833 lines | **HIGH** — always conflicts; regenerate |
| `.gitignore` | Custom rules | Minor changes | **LOW** — distinct additions |
| All other local files | New files or small mods | Not touched by upstream | **NONE** — clean preservation |

## Procedure

### Step 1: Safety Checkpoint
```bash
git status                    # must be clean
git branch backup-jul-2026    # safety backup
git fetch upstream --no-tags  # done
```

### Step 2: Stop Tracking adm.json (pre-merge)
```bash
echo "adm.json" >> .gitignore
git rm --cached adm.json
git add .gitignore
git commit -m "Stop tracking adm.json (local config only)"
```

### Step 3: Execute Merge
```bash
git merge upstream/main
```
Expected: merge conflicts in the files listed above.

### Step 4: Resolve Conflicts (ordered by difficulty)

#### 4a. `.gitignore` (easy)
Accept both sides — our additions + any upstream additions.

#### 4b. `Cargo.toml` (medium)
- Keep our: `version = "0.300.0"`, `codegen-units = 1` in dev, `lto = false` + `debug = 0` in release
- Accept upstream: new workspace members, new dependencies, profile restructuring

#### 4c. `Cargo.lock` (regenerate)
After Cargo.toml resolved, run: `cargo update` or accept upstream's lock then apply our version bumps.

#### 4d. `config/src/config_toml.rs` (medium)
Re-add the `suppress_cyber_safety_warning: Option<bool>` field in the same location relative to upstream's new fields.

#### 4e. `core/src/codex_thread.rs` (high — major upstream restructure)
Upstream has restructured ThreadConfigSnapshot significantly. Key changes to re-apply:
1. Import: `use codex_protocol::config_types::ServiceTier;`
2. Change `service_tier` field type from `Option<String>` to `Option<ServiceTier>`
3. Add `pub suppress_cyber_safety_warning: bool` field

#### 4f. `core/src/config/mod.rs` (highest — massive refactor)
Upstream refactored config loading extensively (1098 lines changed). Our additions:
1. In `Config` struct: add `suppress_cyber_safety_warning: bool` and `active_profile: Option<String>`
2. In Config initialization: add `suppress_cyber_safety_warning: cfg.suppress_cyber_safety_warning.unwrap_or(false)` and `active_profile: active_profile_name`

**Strategy**: The upstream Config struct grew significantly. Locate the `suppress_unstable_features_warning` line (which exists in both versions) and add our fields adjacent to it.

### Step 5: Verify Local Files Preserved
Confirm these files survived the merge intact:
- `.github/workflows/sync-fork.yml`
- `codex-rs/.cargo/config.toml`
- `codex-rs/app-server/tests/suite/user_agent.rs`
- `codex-rs/core/tests/suite/safety_check_downgrade.rs` (our test additions)
- `codex-rs/app-server/tests/suite/v2/safety_check_downgrade.rs` (our test additions)
- `docs/codex-config-cookbook.md`, `docs/codex-config-toml-ref.md`, `docs/config.md`, `docs/search-indexing.md`
- `diagrams/codex_5.3_security.md`, `diagrams/cyber_error_flow.md`, `diagrams/cyber_safety_error.md`, `diagrams/cyber_safety_message.md`, `diagrams/trust_levels.md`

### Step 6: Build Verification
```bash
just write-config-schema    # regenerate config.schema.json with our custom fields
cargo check --workspace     # verify all code compiles
```

### Step 7: Test Verification
```bash
cargo test -p codex-core -- safety_check_downgrade   # verify our tests pass
cargo test -p codex-app-server -- user_agent           # verify our test passes
```

### Step 8: Commit
```
git add -A
git commit -m "Merge upstream/main into Local_Mod (July 2026)
- Preserved: suppress_cyber_safety_warning config
- Preserved: active_profile tracking
- Preserved: ServiceTier type in ThreadConfigSnapshot
- Preserved: Cargo.toml local profile settings
- Removed: adm.json from tracking (gitignored)
- Preserved: custom tests, docs, diagrams"
```

### Step 9: Push
```bash
git push origin Local_Mod
```

## Rollback
If merge goes badly wrong:
```bash
git reset --hard backup-jul-2026   # restore checkpoint
```
Note: Rule 14 prohibits `git reset --hard` generally, but `backup-jul-2026` is our own safety branch created in Step 1 — this is disaster recovery, not history rewrite.

## Verification Checklist
- [ ] Merge completes with conflicts only in expected files
- [ ] `adm.json` is untracked and gitignored
- [ ] All 15 local features preserved (A1-A4, B1-B5, C1-C3, D1-D2)
- [ ] `just write-config-schema` regenerates schema cleanly
- [ ] `cargo check --workspace` passes
- [ ] Our custom tests pass
- [ ] Clean `git status` after commit
