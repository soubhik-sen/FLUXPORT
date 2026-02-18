from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


_OBJECT_TYPES = {"PURCHASE_ORDER", "SHIPMENT"}


def _normalize_object_type(value: str) -> str:
    normalized = (value or "").strip().upper()
    if normalized not in _OBJECT_TYPES:
        raise ValueError("object_type must be PURCHASE_ORDER or SHIPMENT.")
    return normalized


class DocumentLockAcquireRequest(BaseModel):
    object_type: str
    document_id: int = Field(ge=1)
    session_id: str = Field(min_length=3, max_length=120)

    @field_validator("object_type")
    @classmethod
    def validate_object_type(cls, value: str) -> str:
        return _normalize_object_type(value)


class DocumentLockTokenRequest(BaseModel):
    lock_token: str = Field(min_length=10, max_length=300)


class DocumentLockForceReleaseRequest(BaseModel):
    lock_id: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=255)


class DocumentLockView(BaseModel):
    lock_id: int
    object_type: str
    document_id: int
    owner_email: str
    owner_session_id: str
    acquired_at: datetime
    heartbeat_at: datetime
    expires_at: datetime
    is_active: bool
    release_reason: str | None = None


class DocumentLockAcquireResponse(BaseModel):
    lock_id: int
    object_type: str
    document_id: int
    owner_email: str
    acquired_at: datetime
    expires_at: datetime
    ttl_seconds: int
    lock_token: str


class DocumentLockHeartbeatResponse(BaseModel):
    lock_id: int
    expires_at: datetime
    ttl_seconds: int


class DocumentLockReleaseResponse(BaseModel):
    lock_id: int | None = None
    released: bool
    message: str


class DocumentLockListResponse(BaseModel):
    active_locks: list[DocumentLockView]
