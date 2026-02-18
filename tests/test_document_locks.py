from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.models.document_edit_lock import DocumentEditLock
from app.services.document_lock_service import DocumentLockFailure, DocumentLockService


def test_document_lock_same_user_reentry_rotates_token(db_session):
    service = DocumentLockService(db_session)

    first = service.acquire_lock(
        object_type="PURCHASE_ORDER",
        document_id=1001,
        owner_email="user@example.com",
        owner_session_id="sess-a",
    )
    db_session.commit()

    second = service.acquire_lock(
        object_type="PURCHASE_ORDER",
        document_id=1001,
        owner_email="user@example.com",
        owner_session_id="sess-b",
    )
    db_session.commit()

    assert second.lock.id == first.lock.id
    assert second.lock_token != first.lock_token
    assert second.lock.owner_session_id == "sess-b"


def test_document_lock_conflict_for_other_owner(db_session):
    service = DocumentLockService(db_session)

    service.acquire_lock(
        object_type="SHIPMENT",
        document_id=55,
        owner_email="owner@example.com",
        owner_session_id="owner-session",
    )
    db_session.commit()

    with pytest.raises(DocumentLockFailure) as exc_info:
        service.acquire_lock(
            object_type="SHIPMENT",
            document_id=55,
            owner_email="other@example.com",
            owner_session_id="other-session",
        )
    assert exc_info.value.code == "LOCK_CONFLICT"


def test_timeline_save_requires_lock_token_when_enforced(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "DOCUMENT_EDIT_LOCK_ENABLED", True)
    monkeypatch.setattr(settings, "DOCUMENT_EDIT_LOCK_ENFORCE_WRITES", True)

    response = client.post(
        "/api/v1/timeline/save",
        headers={
            "X-User-Email": "user@example.com",
            "Content-Type": "application/json",
        },
        json={
            "object_type": "PURCHASE_ORDER",
            "parent_id": 2001,
            "start_date": "2026-02-18 10:00",
            "recalculate": False,
            "context_data": {},
            "events": [],
        },
    )

    assert response.status_code == 409
    detail = response.json().get("detail") or {}
    assert detail.get("code") == "LOCK_REQUIRED"


def test_timeline_save_with_valid_lock_token_succeeds(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "DOCUMENT_EDIT_LOCK_ENABLED", True)
    monkeypatch.setattr(settings, "DOCUMENT_EDIT_LOCK_ENFORCE_WRITES", True)

    token = "lock-token-123456789"
    token_hash = DocumentLockService._token_hash(token)  # noqa: SLF001
    now = datetime.utcnow()

    db_session.add(
        DocumentEditLock(
            object_type="PURCHASE_ORDER",
            document_id=2002,
            owner_email="user@example.com",
            owner_session_id="sess-1",
            lock_token_hash=token_hash,
            acquired_at=now,
            heartbeat_at=now,
            expires_at=now + timedelta(minutes=10),
            is_active=True,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/timeline/save",
        headers={
            "X-User-Email": "user@example.com",
            "X-Document-Lock-Token": token,
            "Content-Type": "application/json",
        },
        json={
            "object_type": "PURCHASE_ORDER",
            "parent_id": 2002,
            "start_date": "2026-02-18 10:00",
            "recalculate": False,
            "context_data": {},
            "events": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object_type"] == "PURCHASE_ORDER"
    assert payload["parent_id"] == 2002
