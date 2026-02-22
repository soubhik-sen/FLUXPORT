from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.routers.metadata import download_table_template
from app.api.deps.request_identity import get_request_email
from app.core.config import settings
from app.db.session import get_db
from app.services.mass_change_dataset_registry import (
    get_dataset,
    is_phase1_dataset_enabled,
    is_workbook_dataset,
    list_phase1_datasets,
)
from app.services.mass_change_submit_service import (
    purge_expired_batches,
    submit_staged_batch,
    validate_and_stage_batch,
)
from app.services.mass_change_workbook_service import (
    build_workbook_template,
    submit_workbook_batch,
    validate_and_stage_workbook,
)

router = APIRouter(prefix="/mass-change", tags=["mass-change"])


class MassChangeSubmitRequest(BaseModel):
    batch_id: str


def _ensure_enabled() -> None:
    if not settings.MASS_CHANGE_ENABLED:
        raise HTTPException(status_code=404, detail="Mass change cockpit is disabled")


def _require_phase1_dataset(dataset_key: str) -> dict:
    row = get_dataset(dataset_key)
    if not row:
        raise HTTPException(status_code=404, detail=f"Unknown dataset '{dataset_key}'")
    if not is_phase1_dataset_enabled(row):
        raise HTTPException(
            status_code=403,
            detail=f"Dataset '{dataset_key}' is not enabled in Phase 1.",
        )
    return row


@router.get("/datasets")
def list_datasets():
    _ensure_enabled()
    return {"datasets": list_phase1_datasets()}


@router.get("/{dataset_key}/template.xlsx")
def download_dataset_template(
    dataset_key: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _ensure_enabled()
    purge_expired_batches(db)
    dataset = _require_phase1_dataset(dataset_key)
    if is_workbook_dataset(dataset):
        return build_workbook_template(
            db,
            dataset_key=dataset_key,
            user_email=get_request_email(request),
        )
    table_name = str(dataset.get("table_name") or "").strip()
    if not table_name:
        raise HTTPException(status_code=400, detail="Dataset table mapping is missing.")
    return download_table_template(table_name=table_name, db=db)


@router.post("/{dataset_key}/validate")
def validate_dataset_upload(
    dataset_key: str,
    request: Request,
    payload: bytes = Body(...),
    filename: str = Query("upload.xlsx"),
    db: Session = Depends(get_db),
):
    _ensure_enabled()
    dataset = _require_phase1_dataset(dataset_key)
    purge_expired_batches(db)

    filename = (filename or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")

    table_name = str(dataset.get("table_name") or "").strip()
    if not table_name:
        raise HTTPException(status_code=400, detail="Dataset table mapping is missing.")
    user_email = get_request_email(request)
    if is_workbook_dataset(dataset):
        return validate_and_stage_workbook(
            db,
            dataset_key=dataset_key,
            payload=payload,
            filename=filename,
            user_email=user_email,
            table_name=table_name,
        )
    return validate_and_stage_batch(
        db,
        dataset_key=dataset_key,
        table_name=table_name,
        payload=payload,
        filename=filename,
        user_email=user_email,
    )


@router.post("/{dataset_key}/submit")
def submit_dataset_upload(
    dataset_key: str,
    request: Request,
    payload: MassChangeSubmitRequest,
    db: Session = Depends(get_db),
):
    _ensure_enabled()
    dataset = _require_phase1_dataset(dataset_key)
    purge_expired_batches(db)
    user_email = get_request_email(request)
    if is_workbook_dataset(dataset):
        return submit_workbook_batch(
            db,
            dataset_key=dataset_key,
            batch_id=(payload.batch_id or "").strip(),
            user_email=user_email,
        )
    return submit_staged_batch(
        db,
        dataset_key=dataset_key,
        batch_id=(payload.batch_id or "").strip(),
        user_email=user_email,
    )
