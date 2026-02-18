from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.metadata_framework import (
    MetadataAuditLog,
    MetadataRegistry,
    MetadataVersion,
)
from app.services.role_scope_policy_validator import (
    validate_role_scope_policy_payload,
)


@dataclass
class PublishedMetadata:
    type_key: str
    version_no: int
    version_id: int
    payload: dict[str, Any]


class MetadataFrameworkService:
    """
    DB-backed metadata lifecycle service.
    This service is intentionally not wired into existing runtime metadata reads yet.
    """

    @staticmethod
    def list_types(db: Session) -> list[MetadataRegistry]:
        return (
            db.query(MetadataRegistry)
            .order_by(MetadataRegistry.type_key.asc())
            .all()
        )

    @staticmethod
    def get_type(db: Session, type_key: str) -> MetadataRegistry | None:
        return (
            db.query(MetadataRegistry)
            .filter(MetadataRegistry.type_key == type_key)
            .first()
        )

    @staticmethod
    def ensure_type(
        db: Session,
        *,
        type_key: str,
        display_name: str,
        description: str | None = None,
        json_schema: str | None = None,
    ) -> MetadataRegistry:
        existing = MetadataFrameworkService.get_type(db, type_key)
        if existing is not None:
            return existing

        row = MetadataRegistry(
            type_key=type_key.strip(),
            display_name=display_name.strip(),
            description=(description or "").strip() or None,
            json_schema=(json_schema or "").strip() or None,
            is_active=True,
        )
        db.add(row)
        db.flush()
        MetadataFrameworkService._log_action(
            db,
            registry_id=row.id,
            action="TYPE_CREATE",
            actor_email=None,
            note="Metadata type created",
        )
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def save_draft(
        db: Session,
        *,
        type_key: str,
        payload: dict[str, Any],
        actor_email: str | None,
        note: str | None = None,
    ) -> MetadataVersion:
        registry = MetadataFrameworkService.get_type(db, type_key)
        if registry is None:
            raise HTTPException(status_code=404, detail=f"Metadata type not found: {type_key}")

        max_version = (
            db.query(func.max(MetadataVersion.version_no))
            .filter(MetadataVersion.registry_id == registry.id)
            .scalar()
        ) or 0
        version_no = int(max_version) + 1

        row = MetadataVersion(
            registry_id=registry.id,
            version_no=version_no,
            state="DRAFT",
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_by=actor_email,
        )
        db.add(row)
        db.flush()
        MetadataFrameworkService._log_action(
            db,
            registry_id=registry.id,
            action="SAVE_DRAFT",
            actor_email=actor_email,
            to_version_id=row.id,
            note=note,
        )
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_published(db: Session, type_key: str) -> PublishedMetadata | None:
        registry = MetadataFrameworkService.get_type(db, type_key)
        if registry is None:
            return None

        published = (
            db.query(MetadataVersion)
            .filter(MetadataVersion.registry_id == registry.id)
            .filter(MetadataVersion.state == "PUBLISHED")
            .order_by(MetadataVersion.version_no.desc())
            .first()
        )
        if published is None:
            return None

        try:
            payload = json.loads(published.payload_json)
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}
        return PublishedMetadata(
            type_key=registry.type_key,
            version_no=int(published.version_no),
            version_id=int(published.id),
            payload=payload,
        )

    @staticmethod
    def publish(
        db: Session,
        *,
        type_key: str,
        actor_email: str | None,
        version_no: int | None = None,
        note: str | None = None,
    ) -> PublishedMetadata:
        registry = MetadataFrameworkService.get_type(db, type_key)
        if registry is None:
            raise HTTPException(status_code=404, detail=f"Metadata type not found: {type_key}")

        query = (
            db.query(MetadataVersion)
            .filter(MetadataVersion.registry_id == registry.id)
        )
        if version_no is not None:
            candidate = query.filter(MetadataVersion.version_no == int(version_no)).first()
        else:
            candidate = (
                query.filter(MetadataVersion.state == "DRAFT")
                .order_by(MetadataVersion.version_no.desc())
                .first()
            )
        if candidate is None:
            raise HTTPException(status_code=404, detail="No draft/version available to publish")

        payload: dict[str, Any]
        try:
            decoded_payload = json.loads(candidate.payload_json)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON payload for publish candidate: {exc}",
            )
        if not isinstance(decoded_payload, dict):
            raise HTTPException(status_code=400, detail="Metadata payload must be a JSON object")
        payload = decoded_payload

        if registry.type_key == "role_scope_policy":
            validation_errors = validate_role_scope_policy_payload(payload)
            if validation_errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Role scope policy validation failed.",
                        "issues": validation_errors,
                    },
                )

        previous = (
            db.query(MetadataVersion)
            .filter(MetadataVersion.registry_id == registry.id)
            .filter(MetadataVersion.state == "PUBLISHED")
            .all()
        )
        for row in previous:
            row.state = "ARCHIVED"

        candidate.state = "PUBLISHED"
        candidate.published_by = actor_email
        candidate.published_at = datetime.now(timezone.utc)
        db.add(candidate)
        db.flush()

        MetadataFrameworkService._log_action(
            db,
            registry_id=registry.id,
            action="PUBLISH",
            actor_email=actor_email,
            from_version_id=(max((r.id for r in previous), default=None)),
            to_version_id=candidate.id,
            note=note,
        )
        db.commit()
        db.refresh(candidate)

        return PublishedMetadata(
            type_key=registry.type_key,
            version_no=int(candidate.version_no),
            version_id=int(candidate.id),
            payload=payload,
        )

    @staticmethod
    def list_versions(db: Session, type_key: str, limit: int = 50) -> list[MetadataVersion]:
        registry = MetadataFrameworkService.get_type(db, type_key)
        if registry is None:
            return []
        return (
            db.query(MetadataVersion)
            .filter(MetadataVersion.registry_id == registry.id)
            .order_by(MetadataVersion.version_no.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )

    @staticmethod
    def _log_action(
        db: Session,
        *,
        registry_id: int | None,
        action: str,
        actor_email: str | None,
        from_version_id: int | None = None,
        to_version_id: int | None = None,
        note: str | None = None,
    ) -> None:
        entry = MetadataAuditLog(
            registry_id=registry_id,
            action=action,
            actor_email=actor_email,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
            note=note,
        )
        db.add(entry)
