from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import json

import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse
from datetime import datetime
from fnmatch import fnmatchcase

from app.db.session import get_db
from app.core.reports.visibility_config import VISIBILITY_REPORT_CONFIG
from app.core.reports.po_to_group_config import PO_TO_GROUP_REPORT_CONFIG
from app.core.reports.customer_master_config import CUSTOMER_MASTER_REPORT_CONFIG
from app.core.reports.partner_master_config import PARTNER_MASTER_REPORT_CONFIG
from app.core.reports.shipment_report_config import SHIPMENT_REPORT_CONFIG
from app.core.reports.query_engine import ReportQueryEngine
from app.models.user_partner_link import UserPartnerLink
from app.models.user_customer_link import UserCustomerLink
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.customer_master import CustomerMaster
from app.models.purchase_order import PurchaseOrderHeader

router = APIRouter()

REPORT_CONFIGS = {
    VISIBILITY_REPORT_CONFIG["report_id"]: VISIBILITY_REPORT_CONFIG,
    PO_TO_GROUP_REPORT_CONFIG["report_id"]: PO_TO_GROUP_REPORT_CONFIG,
    CUSTOMER_MASTER_REPORT_CONFIG["report_id"]: CUSTOMER_MASTER_REPORT_CONFIG,
    PARTNER_MASTER_REPORT_CONFIG["report_id"]: PARTNER_MASTER_REPORT_CONFIG,
    SHIPMENT_REPORT_CONFIG["report_id"]: SHIPMENT_REPORT_CONFIG,
}

def _get_report_config(report_id: str) -> dict:
    config = REPORT_CONFIGS.get(report_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Unknown report: {report_id}")
    return config

def _get_user_email(request: Request) -> str | None:
    return request.headers.get("X-User-Email") or request.headers.get("X-User")

def _resolve_forwarder_partner_ids(db: Session, user_email: str) -> list[int]:
    return _resolve_partner_ids_by_role_codes(db, user_email, ["FO", "FORWARDER"])

def _resolve_supplier_partner_ids(db: Session, user_email: str) -> list[int]:
    return _resolve_partner_ids_by_role_codes(db, user_email, ["SU", "SUPPLIER"])

def _resolve_partner_ids_by_role_codes(db: Session, user_email: str, role_codes: list[str]) -> list[int]:
    rows = (
        db.query(UserPartnerLink.partner_id)
        .join(PartnerMaster, PartnerMaster.id == UserPartnerLink.partner_id)
        .join(PartnerRole, PartnerRole.id == PartnerMaster.role_id)
        .filter(UserPartnerLink.user_email == user_email)
        .filter(UserPartnerLink.deletion_indicator == False)
        .filter(PartnerRole.role_code.in_(role_codes))
        .all()
    )
    return sorted({r[0] for r in rows if r and r[0] is not None})

def _resolve_customer_ids(db: Session, user_email: str) -> list[int]:
    rows = (
        db.query(UserCustomerLink.customer_id)
        .join(CustomerMaster, CustomerMaster.id == UserCustomerLink.customer_id)
        .filter(UserCustomerLink.user_email == user_email)
        .filter(UserCustomerLink.deletion_indicator == False)
        .filter(CustomerMaster.is_active == True)
        .all()
    )
    return sorted({r[0] for r in rows if r and r[0] is not None})

def _eligible_po_numbers(db: Session, filters: dict, search: Optional[str]) -> list[str]:
    """
    For the grouping tool, include all lines for POs that still have at least
    one unshipped schedule line.
    """
    config = PO_TO_GROUP_REPORT_CONFIG
    engine = ReportQueryEngine(db, config=config)
    sub_filters = dict(filters)
    # Normalize incoming PO filters so wildcard list edge-cases don't collapse the sub-query.
    if "po_no" in sub_filters:
        raw_po_filter = sub_filters.get("po_no")
        if isinstance(raw_po_filter, list):
            values = _normalize_po_filter_values(raw_po_filter)
            if not values:
                sub_filters.pop("po_no", None)
            elif len(values) == 1 and _is_pattern_po_filter_value(values[0]):
                # Single wildcard value can be safely executed as search filter.
                sub_filters["po_no"] = values[0]
            elif all(not _is_pattern_po_filter_value(v) for v in values):
                # Exact list can remain IN-filter.
                sub_filters["po_no"] = values
            else:
                # Mixed values (exact + wildcard) are applied after eligible POs are computed.
                sub_filters.pop("po_no", None)
    sub_filters["shipment_header_id"] = "__NULL__"
    sub_query = engine.build_query(
        select_keys=["po_no"],
        filters=sub_filters,
        search=search,
        include_base_id=False,
    )
    rows = sub_query.all()
    po_numbers = {row.po_no for row in rows if getattr(row, "po_no", None)}
    return sorted(po_numbers)

def _normalize_po_filter_values(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None and str(v).strip()]
    text = str(value).strip()
    return [text] if text else []

def _is_pattern_po_filter_value(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    # Treat wildcard-style values as pattern filters, not explicit PO numbers.
    return any(token in text for token in ("*", "?", "%", "_"))

def _normalize_exact_po_filter_values(value) -> list[str]:
    values = _normalize_po_filter_values(value)
    return [v for v in values if not _is_pattern_po_filter_value(v)]

def _matches_po_filter_value(po_number: str, raw_value: str) -> bool:
    value = (raw_value or "").strip()
    if not value:
        return True
    if _is_pattern_po_filter_value(value):
        pattern = value.replace("%", "*").replace("_", "?")
        return fnmatchcase(po_number.lower(), pattern.lower())
    return po_number == value

def _filter_po_numbers_by_raw_filter(po_numbers: list[str], raw_filter_value) -> list[str]:
    values = _normalize_po_filter_values(raw_filter_value)
    if not values:
        return po_numbers
    filtered: list[str] = []
    for po in po_numbers:
        if any(_matches_po_filter_value(po, raw) for raw in values):
            filtered.append(po)
    return filtered

def _normalize_int_filter_values(value) -> list[int]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    parsed: list[int] = []
    for raw in values:
        try:
            parsed.append(int(str(raw)))
        except (TypeError, ValueError):
            continue
    return parsed

def _apply_scoped_filter(filter_map: dict, key: str, scoped_ids: list[int]) -> bool:
    if not scoped_ids:
        return True
    existing = _normalize_int_filter_values(filter_map.get(key))
    effective = [sid for sid in scoped_ids if not existing or sid in existing]
    if not effective:
        return False
    filter_map[key] = effective
    return True

def _apply_grouping_scope(db: Session, user_email: Optional[str], filter_map: dict) -> bool:
    if not user_email:
        return True
    forwarder_ids = _resolve_forwarder_partner_ids(db, user_email)
    if forwarder_ids:
        return _apply_scoped_filter(filter_map, "forwarder_id", forwarder_ids)
    supplier_ids = _resolve_supplier_partner_ids(db, user_email)
    if supplier_ids:
        return _apply_scoped_filter(filter_map, "vendor_id", supplier_ids)
    customer_ids = _resolve_customer_ids(db, user_email)
    if customer_ids:
        return _apply_scoped_filter(filter_map, "company_id", customer_ids)
    return True

def _resolve_visibility_scoped_po_numbers(db: Session, user_email: Optional[str]) -> list[str]:
    """
    Visibility scope is OR-based across mapped forwarders, suppliers, and customers.
    Strict visibility scope:
      - no authenticated user header => no access
      - no mapped forwarder/supplier/customer => no access
      - otherwise only scoped PO numbers
    """
    if not user_email:
        return []

    forwarder_ids = _resolve_forwarder_partner_ids(db, user_email)
    supplier_ids = _resolve_supplier_partner_ids(db, user_email)
    customer_ids = _resolve_customer_ids(db, user_email)

    clauses = []
    if forwarder_ids:
        clauses.append(PurchaseOrderHeader.carrier_id.in_(forwarder_ids))
    if supplier_ids:
        clauses.append(PurchaseOrderHeader.vendor_id.in_(supplier_ids))
    if customer_ids:
        clauses.append(PurchaseOrderHeader.company_id.in_(customer_ids))

    if not clauses:
        return []

    rows = (
        db.query(PurchaseOrderHeader.po_number)
        .filter(or_(*clauses))
        .all()
    )
    return sorted({r[0] for r in rows if r and r[0]})

def _apply_visibility_scope(db: Session, user_email: Optional[str], filter_map: dict) -> bool:
    scoped_po_numbers = _resolve_visibility_scoped_po_numbers(db, user_email)
    scoped_po_numbers = _filter_po_numbers_by_raw_filter(scoped_po_numbers, filter_map.get("po_no"))
    if not scoped_po_numbers:
        return False
    filter_map["po_no"] = scoped_po_numbers
    return True

@router.get("/{report_id}/export")
async def export_report_excel(
    report_id: str,
    select: str = Query(..., description="Comma-separated list of UI keys"),
    scope: str = Query("visible", regex="^(visible|all)$"),
    sort: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Global search term"),
    filters: Optional[str] = Query(None, description="JSON object of filters"),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Generates an Excel file based on the user's current view or the full catalog.
    """
    config = _get_report_config(report_id)

    if not sort:
        if report_id == PO_TO_GROUP_REPORT_CONFIG["report_id"]:
            sort = "po_no,po_item_no,po_schedule_line_no"
        else:
            sort = config.get("default_sort")

    # 1. Determine the column set
    if scope == "all":
        requested_columns = list(config["fields"].keys())
    else:
        requested_columns = select.split(",")

    filter_map = {}
    if filters:
        try:
            filter_map = json.loads(filters) or {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filters JSON")

    if report_id == PO_TO_GROUP_REPORT_CONFIG["report_id"] and request is not None:
        user_email = _get_user_email(request)
        if not _apply_grouping_scope(db, user_email, filter_map):
            raise HTTPException(status_code=400, detail="No matching POs to export.")
        # For grouping: include all lines for POs that have at least one unshipped line.
        po_numbers = _eligible_po_numbers(db, filter_map, search)
        po_numbers = _filter_po_numbers_by_raw_filter(po_numbers, filter_map.get("po_no"))
        if not po_numbers:
            raise HTTPException(status_code=400, detail="No matching POs to export.")
        filter_map["po_no"] = po_numbers
        search = None
    elif report_id == VISIBILITY_REPORT_CONFIG["report_id"] and request is not None:
        user_email = _get_user_email(request)
        if not _apply_visibility_scope(db, user_email, filter_map):
            raise HTTPException(status_code=400, detail="No matching POs to export.")

    has_filters = any(v not in (None, "", [], {}) for v in filter_map.values())
    has_search = bool(search and search.strip())
    if not has_filters and not has_search:
        raise HTTPException(status_code=400, detail="Export requires a search or filters")

    # 2. Use the same Query Engine (Consistency!)
    engine = ReportQueryEngine(db, config=config)
    query = engine.build_query(
        select_keys=requested_columns,
        sort_by=sort,
        filters=filter_map,
        search=search,
        include_base_id=False,
    )
    
    # We fetch all matching records for export (ignoring UI pagination)
    results = query.all()
    
    # 3. Convert to Dataframe
    # We use the 'Label' from our config as the Excel Header
    column_labels = {
        key: config["fields"][key]["label"] 
        for key in requested_columns
    }
    
    df = pd.DataFrame([dict(row._mapping) for row in results])
    df.rename(columns=column_labels, inplace=True)

    # 4. Stream the File
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=config.get("report_id", "Report"))
        
        # Auto-adjust column width (Enterprise touch)
        worksheet = writer.sheets[config.get("report_id", "Report")]
        for idx, col in enumerate(df.columns):
            col_lengths = df[col].fillna("").astype(str).str.len()
            max_len = max(col_lengths.max() if not col_lengths.empty else 0, len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = max_len

    output.seek(0)
    
    filename = f"{config.get('report_id', 'report').title()}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/{report_id}/metadata")
async def get_report_metadata(report_id: str):
    """
    Returns the configuration to the Flutter UI.
    """
    config = _get_report_config(report_id)
    ui_config = {
        "report_id": config["report_id"],
        "default_columns": config["default_columns"],
        "group_metrics": config.get("group_metrics", []),
        "fields": {
            key: {
                "label": val["label"],
                "label_key": val.get("label_key"),
                "group": val.get("group", "General"),
                "filter_type": val.get("filter_type"),
                "is_filterable": val.get("is_filterable", False), # NEW: Add this
                "options": val.get("options", []),               # NEW: Add this for dropdowns
                "sortable": val.get("sortable", True),
                "width": val.get("width"),
                "editable": val.get("editable"),
                "data_type": val.get("data_type"),
                "formatter": val.get("formatter"),
                "icon_rules": val.get("icon_rules"),
                "hidden": val.get("hidden")
            }
            for key, val in config["fields"].items()
        }
    }
    return ui_config

@router.get("/{report_id}/data")
async def get_report_data(
    report_id: str,
    select: str = Query(..., description="Comma-separated list of UI keys"),
    sort: Optional[str] = Query(None, description="Key name, prefix with '-' for DESC"),
    search: Optional[str] = Query(None, description="Global search term"),
    filters: Optional[str] = Query(None, description="JSON object of filters"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    The main dynamic data endpoint.
    Example: /data?select=po_no,vendor_name,ship_status&sort=-po_date
    """
    config = _get_report_config(report_id)
    if not sort:
        if report_id == PO_TO_GROUP_REPORT_CONFIG["report_id"]:
            sort = "po_no,po_item_no,po_schedule_line_no"
        else:
            sort = config.get("default_sort")
    requested_columns = select.split(",")
    
    # Validation: Ensure all requested columns exist in our config
    for col in requested_columns:
        if col not in config["fields"]:
            raise HTTPException(status_code=400, detail=f"Invalid column: {col}")

    filter_map = {}
    if filters:
        try:
            filter_map = json.loads(filters) or {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filters JSON")

    if report_id == PO_TO_GROUP_REPORT_CONFIG["report_id"] and request is not None:
        user_email = _get_user_email(request)
        if not _apply_grouping_scope(db, user_email, filter_map):
            return {"total": 0, "page": page, "limit": limit, "data": []}
        # For grouping: include all lines for POs that have at least one unshipped line.
        po_numbers = _eligible_po_numbers(db, filter_map, search)
        po_numbers = _filter_po_numbers_by_raw_filter(po_numbers, filter_map.get("po_no"))
        if not po_numbers:
            return {"total": 0, "page": page, "limit": limit, "data": []}
        filter_map["po_no"] = po_numbers
        search = None
    elif report_id == VISIBILITY_REPORT_CONFIG["report_id"] and request is not None:
        user_email = _get_user_email(request)
        if not _apply_visibility_scope(db, user_email, filter_map):
            return {"total": 0, "page": page, "limit": limit, "data": []}

    has_filters = any(v not in (None, "", [], {}) for v in filter_map.values())
    has_search = bool(search and search.strip())
    if not has_filters and not has_search:
        return {"total": 0, "page": page, "limit": limit, "data": []}

    engine = ReportQueryEngine(db, config=config)
    
    # 1. Build the dynamic query
    query = engine.build_query(
        select_keys=requested_columns,
        filters=filter_map,
        sort_by=sort,
        search=search,
        include_base_id=False,
    )
    
    # 2. Add Pagination (Standard Enterprise Requirement)
    total_records = query.count()
    offset = (page - 1) * limit
    results = query.offset(offset).limit(limit).all()

    # 3. Serialize results into a list of dictionaries
    # 'results' contains rows where each attribute matches our UI keys
    data = [dict(row._mapping) for row in results]

    return {
        "total": total_records,
        "page": page,
        "limit": limit,
        "data": data
    }

# --- Legacy Visibility Paths (Backward Compatible) ---
@router.get("/visibility/metadata")
async def get_visibility_metadata():
    return await get_report_metadata(VISIBILITY_REPORT_CONFIG["report_id"])

@router.get("/visibility/data")
async def get_visibility_data(
    select: str = Query(..., description="Comma-separated list of UI keys"),
    sort: Optional[str] = Query(None, description="Key name, prefix with '-' for DESC"),
    search: Optional[str] = Query(None, description="Global search term"),
    filters: Optional[str] = Query(None, description="JSON object of filters"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    request: Request = None,
):
    return await get_report_data(
        VISIBILITY_REPORT_CONFIG["report_id"],
        select=select,
        sort=sort,
        search=search,
        filters=filters,
        page=page,
        limit=limit,
        db=db,
        request=request,
    )

@router.get("/visibility/export")
async def export_visibility_excel(
    select: str = Query(..., description="Comma-separated list of UI keys"),
    scope: str = Query("visible", regex="^(visible|all)$"),
    sort: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Global search term"),
    filters: Optional[str] = Query(None, description="JSON object of filters"),
    db: Session = Depends(get_db),
    request: Request = None,
):
    return await export_report_excel(
        VISIBILITY_REPORT_CONFIG["report_id"],
        select=select,
        scope=scope,
        sort=sort,
        search=search,
        filters=filters,
        db=db,
        request=request,
    )
