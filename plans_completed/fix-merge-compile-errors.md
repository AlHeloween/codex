# Plan: Fix 4 Compile Errors from Merge

## Errors

```
E0425: cannot find value `active_profile_name`        — config/mod.rs:3964
E0308: mismatched types Option<ServiceTier> → String  — session/handlers.rs:180
E0308: mismatched types Option<String> → ServiceTier  — session/session.rs:183
E0063: missing field `suppress_cyber_safety_warning`   — session/session.rs:180
```

## Root Causes

The auto-merge correctly preserved our 3 local features in the source-of-truth files
(`config_toml.rs`, `config/mod.rs::Config` struct, `codex_thread.rs`), but did NOT
propagate changes to **other call sites** that construct or destructure
`ThreadConfigSnapshot`. The upstream refactored these call sites heavily, and
the merge couldn't resolve the semantic mismatches.

## Fixes (all in `codex-rs/core/src/`)

### Fix 1: `active_profile_name` — `config/mod.rs`
**Root**: Upstream removed the `active_profile_name` variable during Config refactoring.
The value now lives in `active_permission_profile: Option<ActivePermissionProfile>`.

**Action**: Insert 2 lines after line 3785 (before `active_permission_profile` is moved):
```rust
let active_profile_name = active_permission_profile.as_ref().map(|p| p.id.clone());
```
Line 3964 `active_profile: active_profile_name,` — no change needed after fix.

### Fix 2: ServiceTier → String — `session/handlers.rs:180`
**Root**: `snapshot.service_tier` is now `Option<ServiceTier>` but the
`ThreadSettingsSnapshot` struct still expects `Option<String>`.

**Action**: Change line 180 from:
```rust
service_tier: snapshot.service_tier,
```
to:
```rust
service_tier: snapshot.service_tier.map(|t| t.request_value().to_string()),
```

### Fix 3: String → ServiceTier — `session/session.rs:183`
**Root**: `self.service_tier` is `Option<String>` but `ThreadConfigSnapshot`
now expects `Option<ServiceTier>`.

**Action**: Change line 183 from:
```rust
service_tier: self.service_tier.clone(),
```
to:
```rust
service_tier: self.service_tier.clone().and_then(|s| ServiceTier::from_request_value(&s)),
```

### Fix 4: Missing `suppress_cyber_safety_warning` — `session/session.rs`
**Root**: `ThreadConfigSnapshot` grew a new field. Session's `thread_config_snapshot()`
method doesn't set it.

**Action**: Insert after line 191 (`ephemeral: ...`) and before line 192 (`reasoning_effort:`):
```rust
            suppress_cyber_safety_warning: self.original_config_do_not_use.suppress_cyber_safety_warning,
```

## Files Modified
| File | Lines | Change |
|------|-------|--------|
| `core/src/config/mod.rs` | +2 | Extract `active_profile_name` from `active_permission_profile` |
| `core/src/session/handlers.rs` | 1 line changed | Convert Option<ServiceTier> → Option<String> |
| `core/src/session/session.rs` | 2 lines changed | Convert Option<String> → Option<ServiceTier> + add missing field |

## Verification
```powershell
cd codex-rs
cargo check -p codex-core
```
Expected: 0 errors, successful compilation.
