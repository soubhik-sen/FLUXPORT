# Role Scope Policy Change Log

## 2026-02-15
- Published metadata type: `role_scope_policy`
- Published version: `10`
- Source file: `app/core/decision/role_scope_policy.default.json`
- Change summary:
  - Added transactional policies for PO initialization, PO schedule merge, shipment create/list/workspace/read/delete.
  - Added report metadata policy coverage.
  - Added master/config governance policy coverage for admin and master data routers.
  - Kept `ADMIN_ORG` bypass semantics and forwarder guard behavior for `customer-forwarders`.
