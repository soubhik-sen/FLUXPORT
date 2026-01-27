# API Surface

This page summarizes the main HTTP endpoints and their roles.

## Base paths

- Root CRUD routers: `/`
- Versioned domain APIs: `/api/v1`
- Number ranges: `/api/v1/sys-number-ranges`
- Reports (visibility): `/api/v1/reports/visibility`

## Core CRUD routers (root)

These follow a consistent REST pattern: list, get, create, update, delete.

- `users` (includes `GET /users/by-email`, delete supports `?mode=soft|hard`)
- `roles`, `permissions`, `role-permissions`
- `user-roles`, `user-departments`, `user-countries`, `user-attributes`
- `object-types`, `domains`, `masteraddr`, `forwarders`
- `metadata` (schema-like table metadata for UI)

## RBAC and access queries

- `GET /user-profile?email=...` or `?username=...`
  - Joined profile response: user + roles + permissions + departments + countries + attributes
- `GET /access-queries/by-permission?permission_id=...`
  - Returns permission, roles containing it, and users in those roles
- `GET /access-queries/by-role?role_id=...` or `?role_name=...`
  - Returns role, permissions, and users holding the role

## Number range management

Base path: `/api/v1/sys-number-ranges`

Supported operations:
- `GET /api/v1/sys-number-ranges` (list)
- `POST /api/v1/sys-number-ranges` (create)
- `PATCH /api/v1/sys-number-ranges/{range_id}` (update)
- `DELETE /api/v1/sys-number-ranges/{range_id}` (delete)

## Lookup factory endpoints

`app/api/v1/endpoints/lookup_factory.py` generates CRUD endpoints for lookup tables defined in
`app/api/v1/endpoints/api.py`. Examples (under `/api/v1`):

- `/uom_lookup`
- `/po_status_lookup`, `/po_type_lookup`, `/purchase_org_lookup`, `/po_item_status_lookup`
- `/shipment_status_lookup`, `/transport_mode_lookup`, `/milestone_type_lookup`, `/container_type_lookup`
- `/cost_component_lookup`
- `/document_type_lookup`, `/text_type_lookup`

These endpoints are created dynamically and share the same CRUD semantics.

## Domain endpoints

### Purchase Orders

Base: `/api/v1/purchase-orders`

- `POST /` creates a PO header + items
- `GET /{po_id}` returns a PO with items and joined lookups
- `GET /` paginated list, supports optional `vendor_id`

### Shipments

Base: `/api/v1/shipments`

- `POST /` creates shipment with validation against PO items
- `GET /{shipment_id}` retrieves shipment with items

### Reports (Visibility)

Base: `/api/v1/reports/visibility`

- `GET /metadata` returns UI metadata for column definitions and filters
- `GET /data` returns report data with pagination
- `GET /export` streams an Excel file based on selected columns

## API contracts

- `openapi.json` is committed at repo root
- `collection.json` provides a Postman collection
