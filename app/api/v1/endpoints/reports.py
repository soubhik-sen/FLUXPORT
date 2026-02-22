from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import json
import logging

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
from app.models.customer_master import CustomerMaster
from app.models.purchase_order import PurchaseOrderHeader
from app.services.role_scope_policy import (
    is_scope_denied,
    resolve_scope_by_field,
    scope_deny_detail,
    sanitize_scope_by_field,
)
from app.api.deps.request_identity import get_request_email
from app.core.flow_logging import flow_info

router = APIRouter()
logger = logging.getLogger(__name__)

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
    return get_request_email(request)


def _legacy_company_ids_for_customer_scope(
    db: Session,
    scope_by_field: dict[str, set[int]],
) -> set[int]:
    customer_ids = scope_by_field.get("customer_id") or set()
    if not customer_ids:
        return set()
    rows = (
        db.query(CustomerMaster.company_id)
        .filter(CustomerMaster.id.in_(sorted(customer_ids)))
        .filter(CustomerMaster.company_id.isnot(None))
        .all()
    )
    return {int(row[0]) for row in rows if row and row[0] is not None}

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

def _resolve_scoped_po_numbers(
    db: Session,
    user_email: Optional[str],
    *,
    strict: bool,
    forwarder_field: str,
    endpoint_key: str = "reports",
    http_method: str = "GET",
    endpoint_path: str | None = None,
) -> tuple[bool, list[str]]:
    """
    Returns (scope_applied, scoped_po_numbers).
    scope_applied=False means no scope restriction should be enforced.
    """
    if not user_email:
        return (strict, [])

    raw_scope = resolve_scope_by_field(
        db,
        user_email=user_email,
        endpoint_key=endpoint_key,
        http_method=http_method,
        endpoint_path=endpoint_path,
    )
    if is_scope_denied(raw_scope):
        return (True, [])
    scope_by_field = sanitize_scope_by_field(raw_scope)
    if not scope_by_field:
        return (strict, [])

    clauses = []
    forwarder_ids = scope_by_field.get("forwarder_id") or set()
    if forwarder_ids:
        clauses.append(
            getattr(PurchaseOrderHeader, forwarder_field).in_(
                sorted(forwarder_ids)
            )
        )
    supplier_ids = scope_by_field.get("vendor_id") or set()
    if supplier_ids:
        clauses.append(PurchaseOrderHeader.vendor_id.in_(sorted(supplier_ids)))
    customer_ids = scope_by_field.get("customer_id") or set()
    if customer_ids:
        clauses.append(PurchaseOrderHeader.customer_id.in_(sorted(customer_ids)))
        legacy_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)
        if legacy_company_ids:
            clauses.append(
                and_(
                    PurchaseOrderHeader.customer_id.is_(None),
                    PurchaseOrderHeader.company_id.in_(sorted(legacy_company_ids)),
                )
            )
    explicit_company_ids = scope_by_field.get("company_id") or set()
    if explicit_company_ids:
        clauses.append(PurchaseOrderHeader.company_id.in_(sorted(explicit_company_ids)))

    if not clauses:
        return (strict, [])

    rows = db.query(PurchaseOrderHeader.po_number).filter(or_(*clauses)).all()
    scoped_po_numbers = sorted({r[0] for r in rows if r and r[0]})
    return (True, scoped_po_numbers)

def _apply_grouping_scope(db: Session, user_email: Optional[str], filter_map: dict) -> bool:
    scope_applied, scoped_po_numbers = _resolve_scoped_po_numbers(
        db,
        user_email,
        strict=False,
        forwarder_field="forwarder_id",
        endpoint_key="reports.po_to_group",
        endpoint_path="/api/v1/reports/po_to_group/data",
    )
    if not scope_applied:
        flow_info(
            logger,
            "po_grouping_scope_not_applied user=%s",
            user_email or "anonymous",
            category="po_grouping",
        )
        return True
    scoped_po_numbers = _filter_po_numbers_by_raw_filter(
        scoped_po_numbers, filter_map.get("po_no")
    )
    if not scoped_po_numbers:
        flow_info(
            logger,
            "po_grouping_scope_empty user=%s",
            user_email or "anonymous",
            category="po_grouping",
        )
        return False
    flow_info(
        logger,
        "po_grouping_scope_applied user=%s scoped_po_count=%s",
        user_email or "anonymous",
        len(scoped_po_numbers),
        category="po_grouping",
    )
    filter_map["po_no"] = scoped_po_numbers
    return True

def _apply_visibility_scope(db: Session, user_email: Optional[str], filter_map: dict) -> bool:
    _, scoped_po_numbers = _resolve_scoped_po_numbers(
        db,
        user_email,
        strict=True,
        forwarder_field="forwarder_id",
        endpoint_key="reports.visibility",
        endpoint_path="/api/v1/reports/procurement_end_to_end/data",
    )
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
async def get_report_metadata(
    report_id: str,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Returns the configuration to the Flutter UI.
    """
    if request is not None:
        user_email = _get_user_email(request)
        raw_scope = resolve_scope_by_field(
            db,
            user_email=user_email,
            endpoint_key="reports.metadata",
            http_method="GET",
            endpoint_path=request.url.path,
        )
        if is_scope_denied(raw_scope):
            raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))

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
        flow_info(
            logger,
            "po_grouping_data_requested user=%s page=%s limit=%s has_search=%s has_filters=%s",
            user_email or "anonymous",
            page,
            limit,
            bool(search and search.strip()),
            bool(filters),
            category="po_grouping",
        )
        if not _apply_grouping_scope(db, user_email, filter_map):
            flow_info(
                logger,
                "po_grouping_data_empty user=%s reason=scope_filtered",
                user_email or "anonymous",
                category="po_grouping",
            )
            return {"total": 0, "page": page, "limit": limit, "data": []}
        # For grouping: include all lines for POs that have at least one unshipped line.
        po_numbers = _eligible_po_numbers(db, filter_map, search)
        po_numbers = _filter_po_numbers_by_raw_filter(po_numbers, filter_map.get("po_no"))
        if not po_numbers:
            flow_info(
                logger,
                "po_grouping_data_empty user=%s reason=no_eligible_po_numbers",
                user_email or "anonymous",
                category="po_grouping",
            )
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
    if report_id == PO_TO_GROUP_REPORT_CONFIG["report_id"] and request is not None:
        flow_info(
            logger,
            "po_grouping_data_returned user=%s total=%s page=%s returned_rows=%s",
            _get_user_email(request) or "anonymous",
            total_records,
            page,
            len(data),
            category="po_grouping",
        )

    return {
        "total": total_records,
        "page": page,
        "limit": limit,
        "data": data
    }

# --- Legacy Visibility Paths (Backward Compatible) ---
@router.get("/visibility/metadata")
async def get_visibility_metadata(
    db: Session = Depends(get_db),
    request: Request = None,
):
    if request is not None:
        user_email = _get_user_email(request)
        raw_scope = resolve_scope_by_field(
            db,
            user_email=user_email,
            endpoint_key="reports.visibility.metadata",
            http_method="GET",
            endpoint_path=request.url.path,
        )
        if is_scope_denied(raw_scope):
            raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    return await get_report_metadata(
        VISIBILITY_REPORT_CONFIG["report_id"],
        db=db,
        request=request,
    )

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
