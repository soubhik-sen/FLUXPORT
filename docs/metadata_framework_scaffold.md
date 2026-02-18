# Metadata Framework Scaffold (Non-Disruptive)

This scaffold is added to prepare DB-backed runtime metadata management without changing existing behavior.

## Current Safety State

1. `METADATA_FRAMEWORK_ENABLED=false` by default.
2. Most frontend/backend metadata reads are unchanged.
3. `role_scope_policy` reader now supports `assets` vs `db` source switching.
4. New framework router is only mounted when explicitly enabled.
5. Existing endpoint logic is still unchanged unless role-scope mode uses metadata (`ROLE_SCOPE_POLICY_MODE=union_metadata`).

## What Was Added

1. Config flags in `app/core/config.py`:
   - `METADATA_FRAMEWORK_ENABLED`
   - `METADATA_FRAMEWORK_READ_MODE` (`assets` by default)
   - `METADATA_FRAMEWORK_CACHE_TTL_SEC`
2. DB model scaffold in `app/models/metadata_framework.py`:
   - `metadata_registry`
   - `metadata_version`
   - `metadata_audit_log`
3. Service layer in `app/services/metadata_framework_service.py`:
   - type registry lookup/creation
   - draft save
   - publish lifecycle
   - published payload read
4. Optional admin router in `app/api/routers/metadata_framework.py`:
   - list types
   - save draft
   - publish
   - get published
   - version history
5. Conditional router wiring in `app/main.py`.
6. Alembic migration for framework tables + seed types:
   - `alembic/versions/b8e4d1a9c3f2_create_metadata_framework_tables.py`
   - seeded type keys:
     - `endpoint_metadata`
     - `ui_text_metadata`
     - `create_po_route_metadata`
     - `role_scope_policy`
7. Runtime read adapter for role-scope metadata in `app/core/decision/role_scope_metadata.py`:
   - `METADATA_FRAMEWORK_READ_MODE=assets` -> file/default behavior
   - `METADATA_FRAMEWORK_READ_MODE=db` (and `METADATA_FRAMEWORK_ENABLED=true`) -> reads published DB payload for `role_scope_policy`, with safe fallback to file/default

## Why This Does Not Impact Current Runtime

1. The framework is dark by default (`METADATA_FRAMEWORK_ENABLED=false`).
2. Existing metadata consumers still use current sources, except role-scope metadata when explicitly switched to `db` mode.
3. Business endpoint behavior remains unchanged unless `ROLE_SCOPE_POLICY_MODE=union_metadata` and role-scope metadata is switched to `db`.

## Next Phase (Controlled)

1. Add migration for framework tables.
2. Add read adapters per metadata type (`assets` vs `db`) controlled by `METADATA_FRAMEWORK_READ_MODE`.
3. Cut over one metadata type at a time with rollback switch.
