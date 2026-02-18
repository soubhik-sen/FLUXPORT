# Role Scope Flags Quick Guide

This is the minimal guide for role-scope behavior switches.

## 1) The only flags you normally need

1. `ROLE_SCOPE_POLICY_ENABLED`
2. `ROLE_SCOPE_POLICY_MODE`
3. `UNION_SCOPE_ENABLED`

Everything else is optional tuning.

## 2) Exact behavior matrix

| Goal | ROLE_SCOPE_POLICY_ENABLED | ROLE_SCOPE_POLICY_MODE | UNION_SCOPE_ENABLED | Result |
|---|---|---|---|---|
| Old precedence behavior | `false` | (ignored) | `false` | Legacy precedence (`forwarder > supplier > customer`) |
| Old union behavior | `false` | (ignored) | `true` | Old union behavior |
| Auto mode (legacy) | `true` | `auto` | `false` | Legacy precedence |
| Auto mode (union) | `true` | `auto` | `true` | Union behavior |
| Force legacy | `true` | `legacy` | (any) | Legacy precedence |
| Force union | `true` | `union` | (any) | Union behavior |
| Metadata-driven policy | `true` | `union_metadata` | (any) | Policy JSON controls allow/scope |

## 3) Metadata mode flags (optional but important)

1. `ROLE_SCOPE_METADATA_PATH`
   - Path to policy JSON.
   - Current default in `.env`:
     - `app/core/decision/role_scope_policy.default.json`
2. `ROLE_SCOPE_METADATA_FALLBACK_TO_UNION`
   - `true`: if metadata gives no scope, fallback to union scope.
   - `false`: no fallback (metadata result is final).
3. `ROLE_SCOPE_ROLLOUT_ENDPOINTS`
   - Empty: apply to all configured endpoints.
   - Comma patterns: apply only selected endpoints (supports wildcard), e.g.
     - `purchase_orders,reports.*,shipments.from_schedule_lines`
4. `METADATA_FRAMEWORK_ENABLED` + `METADATA_FRAMEWORK_READ_MODE`
   - Role-scope metadata source switch:
     - `METADATA_FRAMEWORK_READ_MODE=assets` -> read `ROLE_SCOPE_METADATA_PATH` (or built-in default)
     - `METADATA_FRAMEWORK_READ_MODE=db` with `METADATA_FRAMEWORK_ENABLED=true` -> read published `role_scope_policy` from metadata framework DB
   - If DB read fails or no published version exists, runtime safely falls back to file/default.

## 4) Policy Matching Notes (method/path)

1. `path` is required for path-based matching and supports wildcards (example: `/user-partners*`).
2. `method` is optional:
   - If omitted, policy applies to all HTTP methods on the matched path (`GET`, `POST`, `PATCH`, `DELETE`, etc.).
   - If set (example: `GET`), policy applies only to that method.
3. Use separate policies per method only when you need different behavior by action.

## 5) Audit/debug flags (optional)

1. `ROLE_SCOPE_AUDIT_ENABLED` (`true/false`)
2. `ROLE_SCOPE_AUDIT_VERBOSE` (`true/false`)
3. `ROLE_SCOPE_AUDIT_SAMPLE_RATE` (`0.0` to `1.0`)

## 6) Recommended presets

### A) Keep existing old behavior (no new policy logic)
```env
ROLE_SCOPE_POLICY_ENABLED=false
UNION_SCOPE_ENABLED=true   # or false, depending on your old expected behavior
```

### B) Start metadata rollout safely
```env
ROLE_SCOPE_POLICY_ENABLED=true
ROLE_SCOPE_POLICY_MODE=union_metadata
ROLE_SCOPE_METADATA_PATH=app/core/decision/role_scope_policy.default.json
ROLE_SCOPE_METADATA_FALLBACK_TO_UNION=true
ROLE_SCOPE_ROLLOUT_ENDPOINTS=purchase_orders,reports.*,shipments.from_schedule_lines
```

### C) Strict metadata control (no fallback)
```env
ROLE_SCOPE_POLICY_ENABLED=true
ROLE_SCOPE_POLICY_MODE=union_metadata
ROLE_SCOPE_METADATA_PATH=app/core/decision/role_scope_policy.default.json
ROLE_SCOPE_METADATA_FALLBACK_TO_UNION=false
```

## 7) One-line rule

If `ROLE_SCOPE_POLICY_ENABLED=false`, system preserves historical behavior and uses only `UNION_SCOPE_ENABLED` to choose between old union and old legacy precedence.
