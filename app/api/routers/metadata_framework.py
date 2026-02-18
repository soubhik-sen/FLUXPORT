from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.metadata_framework import (
    MetadataPublishIn,
    MetadataPublishResult,
    MetadataRegistryOut,
    MetadataSaveDraftIn,
    MetadataVersionOut,
)
from app.services.metadata_framework_service import MetadataFrameworkService

router = APIRouter(prefix="/metadata-framework", tags=["metadata-framework"])


def _ensure_enabled() -> None:
    if not settings.METADATA_FRAMEWORK_ENABLED:
        raise HTTPException(status_code=404, detail="Metadata framework is disabled")


def _to_registry_out(row) -> MetadataRegistryOut:
    return MetadataRegistryOut(
        id=row.id,
        type_key=row.type_key,
        display_name=row.display_name,
        description=row.description,
        is_active=bool(row.is_active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_version_out(row) -> MetadataVersionOut:
    try:
        payload = json.loads(row.payload_json)
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    return MetadataVersionOut(
        id=row.id,
        registry_id=row.registry_id,
        version_no=row.version_no,
        state=row.state,
        payload=payload,
        created_by=row.created_by,
        created_at=row.created_at,
        published_by=row.published_by,
        published_at=row.published_at,
    )


@router.get("/types", response_model=list[MetadataRegistryOut])
def list_metadata_types(db: Session = Depends(get_db)):
    _ensure_enabled()
    rows = MetadataFrameworkService.list_types(db)
    return [_to_registry_out(row) for row in rows]


@router.post("/types/{type_key}/draft", response_model=MetadataVersionOut)
def save_metadata_draft(
    type_key: str,
    body: MetadataSaveDraftIn,
    x_user_email: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _ensure_enabled()
    row = MetadataFrameworkService.save_draft(
        db,
        type_key=type_key,
        payload=body.payload,
        actor_email=x_user_email,
        note=body.note,
    )
    return _to_version_out(row)


@router.post("/types/{type_key}/publish", response_model=MetadataPublishResult)
def publish_metadata(
    type_key: str,
    body: MetadataPublishIn,
    x_user_email: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _ensure_enabled()
    result = MetadataFrameworkService.publish(
        db,
        type_key=type_key,
        actor_email=x_user_email,
        version_no=body.version_no,
        note=body.note,
    )
    return MetadataPublishResult(
        type_key=result.type_key,
        published_version_no=result.version_no,
        published_version_id=result.version_id,
    )


@router.get("/types/{type_key}/published", response_model=MetadataVersionOut)
def get_published_metadata(type_key: str, db: Session = Depends(get_db)):
    _ensure_enabled()
    published = MetadataFrameworkService.get_published(db, type_key)
    if not published:
        raise HTTPException(status_code=404, detail="No published metadata for this type")
    return MetadataVersionOut(
        id=published.version_id,
        registry_id=0,
        version_no=published.version_no,
        state="PUBLISHED",
        payload=published.payload,
        created_by=None,
        created_at=None,
        published_by=None,
        published_at=None,
    )


@router.get("/types/{type_key}/versions", response_model=list[MetadataVersionOut])
def list_metadata_versions(
    type_key: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _ensure_enabled()
    rows = MetadataFrameworkService.list_versions(db, type_key, limit=limit)
    return [_to_version_out(row) for row in rows]
