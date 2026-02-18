from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import secrets

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document_edit_lock import DocumentEditLock

LOCK_TOKEN_HEADER = "X-Document-Lock-Token"


@dataclass
class DocumentLockFailure(Exception):
    code: str
    message: str
    status_code: int = 409
    locked_by: str | None = None
    expires_at: datetime | None = None

    def to_detail(self) -> dict:
        detail = {"code": self.code, "message": self.message}
        if self.locked_by:
            detail["locked_by"] = self.locked_by
        if self.expires_at is not None:
            detail["expires_at"] = self.expires_at.isoformat()
        return detail


@dataclass
class DocumentLockAcquireResult:
    lock: DocumentEditLock
    lock_token: str


class DocumentLockService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _new_token() -> str:
        return secrets.token_urlsafe(36)

    @staticmethod
    def _normalized_email(value: str | None) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _normalized_object_type(value: str | None) -> str:
        normalized = (value or "").strip().upper()
        if normalized not in {"PURCHASE_ORDER", "SHIPMENT"}:
            raise ValueError("object_type must be PURCHASE_ORDER or SHIPMENT.")
        return normalized

    @staticmethod
    def _ttl() -> int:
        return max(30, int(settings.DOCUMENT_EDIT_LOCK_TTL_SECONDS))

    def _touch_expiry(self, lock: DocumentEditLock) -> None:
        now = self._now()
        ttl = self._ttl()
        lock.heartbeat_at = now
        lock.expires_at = now + timedelta(seconds=ttl)
        lock.updated_at = now

    def _expire_if_stale(self, lock: DocumentEditLock) -> bool:
        if not lock.is_active:
            return True
        now = self._now()
        if lock.expires_at is not None and lock.expires_at <= now:
            lock.is_active = False
            lock.released_at = now
            lock.released_by = "system@local"
            lock.release_reason = "expired"
            return True
        return False

    def _active_doc_lock(
        self,
        *,
        object_type: str,
        document_id: int,
        for_update: bool,
    ) -> DocumentEditLock | None:
        query = (
            self.db.query(DocumentEditLock)
            .filter(DocumentEditLock.object_type == object_type)
            .filter(DocumentEditLock.document_id == document_id)
            .filter(DocumentEditLock.is_active.is_(True))
            .order_by(DocumentEditLock.id.desc())
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    def acquire_lock(
        self,
        *,
        object_type: str,
        document_id: int,
        owner_email: str,
        owner_session_id: str,
    ) -> DocumentLockAcquireResult:
        object_type = self._normalized_object_type(object_type)
        owner_email = self._normalized_email(owner_email)
        if not owner_email:
            raise DocumentLockFailure(
                code="LOCK_REQUIRED",
                message="Authenticated user is required to acquire lock.",
            )
        session_id = (owner_session_id or "").strip()
        if not session_id:
            raise DocumentLockFailure(
                code="LOCK_REQUIRED",
                message="session_id is required.",
                status_code=400,
            )

        existing = self._active_doc_lock(
            object_type=object_type,
            document_id=document_id,
            for_update=True,
        )
        if existing is not None and self._expire_if_stale(existing):
            existing = None

        lock_token = self._new_token()
        lock_hash = self._token_hash(lock_token)
        now = self._now()
        expiry = now + timedelta(seconds=self._ttl())

        if existing is not None:
            existing_owner = self._normalized_email(existing.owner_email)
            if existing_owner != owner_email:
                raise DocumentLockFailure(
                    code="LOCK_CONFLICT",
                    message="Document is locked by another user.",
                    locked_by=existing.owner_email,
                    expires_at=existing.expires_at,
                )
            existing.owner_session_id = session_id
            existing.lock_token_hash = lock_hash
            existing.acquired_at = now
            existing.heartbeat_at = now
            existing.expires_at = expiry
            existing.released_at = None
            existing.released_by = None
            existing.release_reason = None
            existing.is_active = True
            return DocumentLockAcquireResult(lock=existing, lock_token=lock_token)

        lock = DocumentEditLock(
            object_type=object_type,
            document_id=document_id,
            owner_email=owner_email,
            owner_session_id=session_id,
            lock_token_hash=lock_hash,
            acquired_at=now,
            heartbeat_at=now,
            expires_at=expiry,
            is_active=True,
        )
        self.db.add(lock)
        self.db.flush()
        return DocumentLockAcquireResult(lock=lock, lock_token=lock_token)

    def heartbeat(
        self,
        *,
        lock_token: str,
        owner_email: str,
    ) -> DocumentEditLock:
        token = (lock_token or "").strip()
        if not token:
            raise DocumentLockFailure(code="LOCK_REQUIRED", message="lock token is required.")
        owner_email = self._normalized_email(owner_email)
        lock_hash = self._token_hash(token)
        lock = (
            self.db.query(DocumentEditLock)
            .filter(DocumentEditLock.lock_token_hash == lock_hash)
            .filter(DocumentEditLock.is_active.is_(True))
            .with_for_update()
            .order_by(DocumentEditLock.id.desc())
            .first()
        )
        if lock is None:
            raise DocumentLockFailure(code="LOCK_CONFLICT", message="Lock token is invalid.")
        if self._expire_if_stale(lock):
            raise DocumentLockFailure(
                code="LOCK_EXPIRED",
                message="Lock has expired.",
                locked_by=lock.owner_email,
                expires_at=lock.expires_at,
            )
        if self._normalized_email(lock.owner_email) != owner_email:
            raise DocumentLockFailure(
                code="LOCK_NOT_OWNER",
                message="Lock is owned by another user.",
                locked_by=lock.owner_email,
                expires_at=lock.expires_at,
            )
        self._touch_expiry(lock)
        return lock

    def release(
        self,
        *,
        lock_token: str,
        owner_email: str,
    ) -> DocumentEditLock | None:
        token = (lock_token or "").strip()
        if not token:
            return None
        owner_email = self._normalized_email(owner_email)
        lock_hash = self._token_hash(token)
        lock = (
            self.db.query(DocumentEditLock)
            .filter(DocumentEditLock.lock_token_hash == lock_hash)
            .filter(DocumentEditLock.is_active.is_(True))
            .with_for_update()
            .order_by(DocumentEditLock.id.desc())
            .first()
        )
        if lock is None:
            return None
        if self._normalized_email(lock.owner_email) != owner_email:
            raise DocumentLockFailure(
                code="LOCK_NOT_OWNER",
                message="Lock is owned by another user.",
                locked_by=lock.owner_email,
                expires_at=lock.expires_at,
            )
        now = self._now()
        lock.is_active = False
        lock.released_at = now
        lock.released_by = owner_email
        lock.release_reason = "released_by_owner"
        lock.updated_at = now
        return lock

    def force_release(
        self,
        *,
        lock_id: int,
        admin_email: str,
        reason: str | None = None,
    ) -> DocumentEditLock:
        admin_email = self._normalized_email(admin_email)
        lock = (
            self.db.query(DocumentEditLock)
            .filter(DocumentEditLock.id == int(lock_id))
            .with_for_update()
            .first()
        )
        if lock is None:
            raise DocumentLockFailure(
                code="LOCK_CONFLICT",
                message="Lock was not found.",
                status_code=404,
            )
        if lock.is_active:
            now = self._now()
            lock.is_active = False
            lock.released_at = now
            lock.released_by = admin_email or "system@local"
            lock.release_reason = (reason or "").strip() or "force_released_by_admin"
            lock.updated_at = now
        return lock

    def list_active_locks(self) -> list[DocumentEditLock]:
        rows = (
            self.db.query(DocumentEditLock)
            .filter(DocumentEditLock.is_active.is_(True))
            .order_by(DocumentEditLock.expires_at.asc(), DocumentEditLock.id.asc())
            .all()
        )
        active: list[DocumentEditLock] = []
        for row in rows:
            if self._expire_if_stale(row):
                continue
            active.append(row)
        return active

    def validate_for_write(
        self,
        *,
        object_type: str,
        document_id: int,
        owner_email: str,
        lock_token: str | None,
    ) -> DocumentEditLock | None:
        if not settings.DOCUMENT_EDIT_LOCK_ENABLED:
            return None
        if not settings.DOCUMENT_EDIT_LOCK_ENFORCE_WRITES:
            return None

        object_type = self._normalized_object_type(object_type)
        owner_email = self._normalized_email(owner_email)
        token = (lock_token or "").strip()
        if not token:
            raise DocumentLockFailure(
                code="LOCK_REQUIRED",
                message="Change mode lock is required for save.",
            )

        lock = self._active_doc_lock(
            object_type=object_type,
            document_id=int(document_id),
            for_update=True,
        )
        if lock is None:
            raise DocumentLockFailure(
                code="LOCK_CONFLICT",
                message="No active lock found for this document.",
            )
        if self._expire_if_stale(lock):
            raise DocumentLockFailure(
                code="LOCK_EXPIRED",
                message="Lock has expired.",
                locked_by=lock.owner_email,
                expires_at=lock.expires_at,
            )
        if self._normalized_email(lock.owner_email) != owner_email:
            raise DocumentLockFailure(
                code="LOCK_NOT_OWNER",
                message="Document is locked by another user.",
                locked_by=lock.owner_email,
                expires_at=lock.expires_at,
            )
        incoming_hash = self._token_hash(token)
        if lock.lock_token_hash != incoming_hash:
            raise DocumentLockFailure(
                code="LOCK_CONFLICT",
                message="Stale lock token. Please re-enter Change Mode.",
                locked_by=lock.owner_email,
                expires_at=lock.expires_at,
            )
        return lock
