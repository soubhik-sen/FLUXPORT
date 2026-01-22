from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse
from datetime import datetime

from app.db.session import get_db
from app.core.reports.visibility_config import VISIBILITY_REPORT_CONFIG
from app.core.reports.query_engine import ReportQueryEngine

router = APIRouter()

@router.get("/export")
async def export_report_excel(
    select: str = Query(..., description="Comma-separated list of UI keys"),
    scope: str = Query("visible", regex="^(visible|all)$"),
    sort: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Generates an Excel file based on the user's current view or the full catalog.
    """
    # 1. Determine the column set
    if scope == "all":
        requested_columns = list(VISIBILITY_REPORT_CONFIG["fields"].keys())
    else:
        requested_columns = select.split(",")

    # 2. Use the same Query Engine (Consistency!)
    engine = ReportQueryEngine(db)
    query = engine.build_query(select_keys=requested_columns, sort_by=sort)
    
    # We fetch all matching records for export (ignoring UI pagination)
    results = query.all()
    
    # 3. Convert to Dataframe
    # We use the 'Label' from our config as the Excel Header
    column_labels = {
        key: VISIBILITY_REPORT_CONFIG["fields"][key]["label"] 
        for key in requested_columns
    }
    
    df = pd.DataFrame([dict(row._mapping) for row in results])
    df.rename(columns=column_labels, inplace=True)

    # 4. Stream the File
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Visibility Report')
        
        # Auto-adjust column width (Enterprise touch)
        worksheet = writer.sheets['Visibility Report']
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = max_len

    output.seek(0)
    
    filename = f"Visibility_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/metadata")
async def get_report_metadata():
    """
    Returns the configuration to the Flutter UI.
    The UI uses this to build the 'Column Settings' and 'Filter Bar'.
    """
    # We strip the technical 'path' (SQLAlchemy objects) before sending to UI
    ui_config = {
        "report_id": VISIBILITY_REPORT_CONFIG["report_id"],
        "default_columns": VISIBILITY_REPORT_CONFIG["default_columns"],
        "fields": {
            key: {
                "label": val["label"],
                "group": val.get("group", "General"),
                "filter_type": val.get("filter_type"),
                "sortable": val.get("sortable", True),
                "formatter": val.get("formatter"),
                "icon_rules": val.get("icon_rules")
            }
            for key, val in VISIBILITY_REPORT_CONFIG["fields"].items()
        }
    }
    return ui_config

@router.get("/data")
async def get_report_data(
    select: str = Query(..., description="Comma-separated list of UI keys"),
    sort: Optional[str] = Query(None, description="Key name, prefix with '-' for DESC"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """
    The main dynamic data endpoint.
    Example: /data?select=po_no,vendor_name,ship_status&sort=-po_date
    """
    requested_columns = select.split(",")
    
    # Validation: Ensure all requested columns exist in our config
    for col in requested_columns:
        if col not in VISIBILITY_REPORT_CONFIG["fields"]:
            raise HTTPException(status_code=400, detail=f"Invalid column: {col}")

    engine = ReportQueryEngine(db)
    
    # 1. Build the dynamic query
    query = engine.build_query(select_keys=requested_columns, sort_by=sort)
    
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