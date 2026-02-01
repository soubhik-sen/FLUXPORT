# Developer Implementation & Extension Guide

Scope: This guide explains how to maintain, reuse, and extend the metadata-driven architecture across the FastAPI backend and Flutter frontend. It is written for new developers onboarding into this repository.

---

## 1) Core Architecture Overview (Source of Truth)

### Backend Source of Truth
- **SQLAlchemy models** in `app/models` define the physical schema.
- **Pydantic schemas** in `app/schemas` define API contract and validation.
- **Metadata endpoint** in `app/api/routers/metadata.py` reflects DB columns to UI-friendly metadata.
- **Lookup factory** in `app/api/v1/endpoints/lookup_factory.py` generates CRUD for lookup tables based on model + schema.
- **Reports** are driven by config dictionaries in `app/core/reports/*_config.py` and executed by `app/core/reports/query_engine.py`.

### Frontend Source of Truth
- **Dynamic tables** are driven by the backend metadata endpoint and the table data endpoint.
- **Dynamic forms** for PO creation are driven by JSON config and lookup data in `assets/json` plus translations in `assets/lang`.
- **Reports UI** consumes report metadata and data via `lib/pages/smart_report_page.dart` and `lib/widgets/smart_report_table.dart`.

### Data Flow (Field-to-UI)
1. **Add DB field** in SQLAlchemy model + Alembic migration.
2. **Expose via API schema** in Pydantic if the endpoint is strongly typed (non-dynamic).
3. **Metadata endpoint** (`/metadata/{table}`) auto-exposes new DB columns for dynamic tables.
4. **Flutter DynamicUserTable** fetches metadata + data and renders new fields automatically.
5. **JSON-driven screens** (e.g., PO Create) require config updates in `assets/json` and translations in `assets/lang`.

---

## 2) Extension Area: Dynamic Table Maintenance (Master Data)

This covers lookup/master tables that use the **metadata-driven CRUD** and show in the dynamic table UI.

### Step-by-Step: Add a New Master Data Table (Example: Product Categories)

**Backend**
1) **Create model**
   - Add a SQLAlchemy model in `app/models/product_lookups.py` (or new module).
   - Example fields: `id`, `category_code`, `category_name`, `is_active`.

2) **Create Pydantic schema**
   - Add in `app/schemas/lookups.py` (pattern: `SomethingLookupSchema`).

3) **Register lookup router**
   - Update `app/api/v1/endpoints/api.py` and append to `LOOKUP_CONFIG`.

**Example (lookup registration in `api.py`)**
```python
LOOKUP_CONFIG = [
  # ...
  {"model": ProductCategoryLookup, "schema": ProductCategoryLookupSchema, "prefix": "/product_category_lookup", "tags": ["Lookups | Product"]},
]
```

4) **Migration**
   - Create Alembic revision and add table.
   - Run `alembic upgrade head`.

**Frontend**
1) **Add sidebar entry**
   - Add a new menu item in `lib/home_screeny.dart` under Configuration or Master Data to load `DynamicUserTable` with `tableKey: "product_category_lookup"`.

2) **No UI code required** for columns or CRUD:
   - `DynamicUserTable` fetches metadata from `/metadata/{table}`.
   - `UserService` routes lookup tables to `api/v1/{table}` automatically.

### Dynamic Table Metadata Rules
Metadata comes from `app/api/routers/metadata.py`:
- Label defaults to Title Case of the column name.
- `LABEL_OVERRIDES` can be used for human-friendly labels.
- Searchable fields are string/bool by default.

**Override example** (in `metadata.py`):
```python
LABEL_OVERRIDES = {
  "product_category_lookup": {
    "category_code": "Category Code",
    "category_name": "Category Name",
  }
}
```

---

## 3) Extension Area: UI Field Management (Metadata-Driven Forms)

Two patterns exist:
1) **Dynamic table forms** (auto-generated from `/metadata`).
2) **JSON-driven forms** (PO Create, etc.).

### A) Add a new field using metadata (Dynamic Table)
Example: Add `middle_name` to `users` (dynamic table)
1) Add column via Alembic + SQLAlchemy model.
2) Metadata endpoint exposes it automatically.
3) DynamicUserTable & DynamicFormDialog render it automatically.

No frontend code or JSON is needed if the table uses `DynamicUserTable`.

### B) Add a field via JSON config (PO Create)
**JSON config is the UI metadata** for PO Create:
`assets/json/po_create_config.json` + translations in `assets/lang/en.json`.

**Example field snippet** (PO Create JSON):
```json
{ "id": "middle_name", "type": "text", "label_key": "FLD_MIDDLE_NAME", "mandatory": false }
```
Add translation in `assets/lang/en.json`:
```json
"FLD_MIDDLE_NAME": "MIDDLE NAME"
```

If the field is a lookup:
```json
{ "id": "buyer_entity", "type": "lookup", "label_key": "FLD_BUYER_ENTITY", "mandatory": true, "lookup_id": "LKP_BUYER_ENTITIES" }
```

Then ensure lookup data is present in `assets/json/po_lookup_data.json` or hydrated from backend initialization in `lib/pages/create_po.dart`.

---

## 4) Developer FAQs

### Q1: How do I add custom validation logic that metadata can’t handle?
**Answer:** Put validation in the backend service layer, not in metadata.
- Example: `app/services/customer_service.py` enforces required `customer_group` and uses NumberRangeService.
- For lookup tables, validation is centralized in `lookup_factory.py` by mapping `code/name` to actual columns.
- For PO creation, validation logic lives in `app/services/purchase_order_service.py`.

### Q2: Why isn’t my new field showing up in the search box?
**Answer:** Search input fields are driven by `isSearchable` in metadata.
- `app/api/routers/metadata.py` marks string/bool columns searchable by default.
- If you need to override, add `LABEL_OVERRIDES` and update `_is_searchable` or create a custom search screen for that table.

### Q3: How do I extend a standard lookup table with extra attributes?
**Answer:** Add new columns to the model and schema and re-run migrations.
- The dynamic form will render the extra attributes automatically.
- If you want a special UI control (e.g., dropdown), you need a custom Flutter form (not DynamicFormDialog).

---

## 5) Reusability Patterns (Generic Components)

### Backend
- **CRUDBase** (used by lookup_factory): `app/crud/base_lookup.py`  
  Generic CRUD for lookups.
- **ReportQueryEngine**: `app/core/reports/query_engine.py`  
  Centralized query builder driven by config dictionaries.
- **NumberRangeService**: `app/services/number_range_get.py`  
  Standard generator for identifiers.
- **AuditMixin**: `app/models/mixins.py`  
  Standard created/updated audit columns.

### Frontend
- **DynamicUserTable**: `lib/widgets/dynamic_user_table.dart`  
  Metadata-driven tables with CRUD and filter bar.
- **DynamicFormDialog**: `lib/widgets/dynamic_form_dialog.dart`  
  Auto-renders form fields from metadata types.
- **POFormEngine**: `lib/widgets/po_form_engine.dart`  
  Renders JSON-defined sections/fields.
- **SmartReportPage + SmartReportTable**:  
  `lib/pages/smart_report_page.dart`, `lib/widgets/smart_report_table.dart`  
  Uses report metadata to render columns/filters and loads data by report_id.
- **UserService**: `lib/services/user_service.dart`  
  Centralized HTTP with routing for lookup vs. core tables.

---

## 6) Configuration Lookup Table (Backend Registration)

Lookup tables are registered in `app/api/v1/endpoints/api.py` via `LOOKUP_CONFIG`.  
Use this registry to expose the table in Swagger + dynamic UI.

| Field | Purpose | Example |
|---|---|---|
| `model` | SQLAlchemy model class | `UomLookup` |
| `schema` | Pydantic schema | `UomLookupSchema` |
| `prefix` | Route prefix | `/uom_lookup` |
| `tags` | Swagger tag | `Lookups | Product` |

---

## 7) Reporting (Smart Reports)

Reports are config-driven and require **no frontend grid changes**.

Backend:
- Configs: `app/core/reports/*_config.py`
- Engine: `app/core/reports/query_engine.py`
- Endpoints: `app/api/v1/endpoints/reports.py` (`/api/v1/reports/{report_id}/metadata|data|export`)

Frontend:
- `lib/pages/smart_report_page.dart` fetches metadata and handles filters.
- `lib/widgets/smart_report_table.dart` renders rows/columns.

To add a new report:
1) Create a new config file with `report_id`, `base_model`, `fields`, `default_columns`.
2) Register it in `reports.py`.
3) Add a sidebar entry to point to that report_id.

---

## 8) Migration Guidance

For any schema change:
1) Update SQLAlchemy models.
2) Generate Alembic revision in `alembic/versions`.
3) Run `alembic upgrade head`.

Use small migrations and avoid touching unrelated tables.

---

## 9) Quick Reference: Key Paths

Backend:
- Models: `app/models`
- Schemas: `app/schemas`
- Metadata endpoint: `app/api/routers/metadata.py`
- Lookup factory: `app/api/v1/endpoints/lookup_factory.py`
- Reports config: `app/core/reports`
- Services: `app/services`
- Migrations: `alembic/versions`

Frontend:
- Dynamic tables: `lib/widgets/dynamic_user_table.dart`
- Dynamic forms: `lib/widgets/dynamic_form_dialog.dart`
- JSON-driven forms: `assets/json/*.json`
- Reports UI: `lib/pages/smart_report_page.dart`, `lib/widgets/smart_report_table.dart`
- Sidebar routing: `lib/home_screeny.dart`
