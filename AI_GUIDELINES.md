# Backend AI Guidelines (Python/SQLAlchemy)

## 🏛 Core Principles
- **Enterprise Integrity:** Ensure strict Foreign Key constraints and data normalization.
- **Fail Loudly:** Use explicit exceptions for procurement logic; never fail silently.
- **Service-Oriented:** Logic resides in `app/services/`. Models are for structure, not business rules.

## 🐍 Logic & Style
- **Type Hints:** Mandatory for all function signatures.
- **Functions over Classes:** Prefer pure functions for domain logic; classes for stateful services only.
- **Naming:** `snake_case` for all Python identifiers. Verbs for functions, nouns for data.
-

## 🏗 Relationship Architecture
- **Partner Pattern:** All external entities (Suppliers, Forwarders, Customers) must use `PartnerMaster`.
- **Branching Logic:** Use association tables (e.g., `supplier`, `forwarder`) to link sites to Main Branches. No separate HQ tables.
- **Lookup Tables:** Never hardcode "Status" or "Role" strings. Reference `_lookup` tables via Foreign Keys.

## 📦 Material Master Standards
- **Global vs Local:** Distinguish between global material data and plant-specific settings.
- **UOM Integrity:** Always validate transactions against the `material_uom_conversion` table.
- **Trilingual First:** Never store descriptions in the `material_master` table; use `material_text`.

## 🤝 Material-Partner Linkage
- **Cross-Reference Mandatory:** When creating a PO, validate the Material/Supplier link in `material_supplier_map`.
- **Alias Handling:** Always prioritize `supplier_part_number` or `customer_part_number` on external documents over internal IDs.
- **Role Validation:** Ensure the `partner_id` in these maps matches the appropriate role (SUPPLIER or CUSTOMER) defined in `partner_role_mapping`.

## 🚫 What NOT to Do
- **No Async:** Do not introduce `async/await` unless explicitly requested.
- **No Domain I/O:** Do not access the DB inside core domain logic functions.
- **No Refactors:** Do not touch Auth0 or DB base classes unless specifically asked.

## 📅 Event & Milestone Logic
- **Automated Determination:** Use the Decision Table (Zen) to determine the "Expected Event" profile based on PO/Shipment attributes (Incoterm, Mode, Route).
- **Decoupled Definitions:** Event definitions stay in `event_master_lookup`; specific instance tracking stays in `expected_event_log`.
- **Logic Rule:** Never hardcode "If PO is International, add Customs Event" in Python. Move this to the Rule Engine.

## role-scope policy or role-scope mapping
For any change to role-scope policy or role-scope mapping:
Update role_scope_policy.default.json.
Publish the same updated payload to metadata framework DB (type_key=role_scope_policy).
Verify DB published version contains the change.
Record resulting version number in the task output.
If DB publish is not possible, state that runtime will still use old DB policy and mark task incomplete.