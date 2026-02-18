from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetadataRegistryOut(BaseModel):
    id: int
    type_key: str
    display_name: str
    description: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MetadataVersionOut(BaseModel):
    id: int
    registry_id: int
    version_no: int
    state: str
    payload: dict[str, Any]
    created_by: str | None = None
    created_at: datetime | None = None
    published_by: str | None = None
    published_at: datetime | None = None


class MetadataSaveDraftIn(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=1000)


class MetadataPublishIn(BaseModel):
    version_no: int | None = None
    note: str | None = Field(default=None, max_length=1000)


class MetadataPublishResult(BaseModel):
    type_key: str
    published_version_no: int
    published_version_id: int
