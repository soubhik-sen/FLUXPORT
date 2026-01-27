from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/metadata", tags=["metadata"])


# Optional: per-table/per-column label overrides
LABEL_OVERRIDES: dict[str, dict[str, str]] = {
    "users": {
        "id": "ID",
        "username": "User Name",
        "email": "Email",
        "clearance": "Clearance",
        "is_active": "Active",
    },
    "sys_number_ranges": {
        "doc_category": "Category",
        "doc_type_id": "Type ID",
        "prefix": "Prefix",
        "current_value": "Last Number",
        "padding": "Padding",
        "include_year": "Include Year?",
        "is_active": "Status"
    },
    "sys_workflow_rules": {
        "doc_category": "Category",
        "doc_type_id": "Type ID",
        "state_code": "Current Status",
        "action_key": "Action",
        "required_role_id": "Required Role",
        "is_blocking": "Blocking"
    },
    "currency_lookup": {
        "currency_code": "Currency Code",
        "currency_name": "Currency Name",
        "is_active": "Active"
    }
}


def _labelize(table_name: str, col_name: str) -> str:
    # Use override if present, else snake_case -> Title Case
    table_overrides = LABEL_OVERRIDES.get(table_name, {})
    if col_name in table_overrides:
        return table_overrides[col_name]
    return col_name.replace("_", " ").strip().title()


def _simple_type(sql_type) -> str:
    # Convert SQLAlchemy type to simple string for UI
    t = sql_type.__class__.__name__.lower()

    if "integer" in t or t in ("int", "bigint", "smallint"):
        return "int"
    if "boolean" in t:
        return "bool"
    if "numeric" in t or "decimal" in t:
        return "decimal"
    if "float" in t or "real" in t:
        return "float"
    if "date" == t:
        return "date"
    if "datetime" in t or "timestamp" in t:
        return "datetime"
    if "uuid" in t:
        return "uuid"
    if "json" in t:
        return "json"
    if "text" in t or "string" in t or "varchar" in t or "char" in t:
        return "string"

    # fallback
    return "string"


def _is_searchable(col_name: str, simple_type: str, is_pk: bool) -> bool:
    # Match your example: id not searchable; string/bool searchable by default
    if is_pk:
        return False
    if simple_type in ("string", "bool"):
        return True
    return False


@router.get("/{table_name}")
def get_table_metadata(table_name: str, db: Session = Depends(get_db)):
    engine = db.get_bind()
    insp = inspect(engine)

    if table_name not in insp.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    cols = insp.get_columns(table_name)
    pk = insp.get_pk_constraint(table_name) or {}
    pk_cols = set(pk.get("constrained_columns") or [])

    result_cols = []
    for c in cols:
        col_name = c["name"]
        stype = _simple_type(c["type"])
        is_pk_col = col_name in pk_cols

        result_cols.append(
            {
                "key": col_name,
                "label": _labelize(table_name, col_name),
                "type": stype,
                "isSearchable": _is_searchable(col_name, stype, is_pk_col),
            }
        )

    return {"tableName": table_name, "columns": result_cols}
