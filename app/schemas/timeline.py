from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TimelineDryRunRequest(BaseModel):
    context_data: dict[str, Any] = Field(
        description=(
            "Rule context for profile and inclusion resolution. "
            "When EVENTS_PROFILE_ENABLED=true include profile_rule_slug; "
            "otherwise include object_type for default profile resolution."
        )
    )
    start_date: datetime


class TimelineDryRunItem(BaseModel):
    event_code: str
    planned_date: datetime | None = None
    is_active: bool


class TimelinePreviewRequest(BaseModel):
    object_type: str = Field(description="Supported values: PURCHASE_ORDER, SHIPMENT")
    parent_id: int = Field(ge=1)
    start_date: datetime
    context_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Context payload used by profile and inclusion rules.",
    )
    preserve_actual_dates: bool = True
    actual_date_overrides: dict[str, datetime] = Field(
        default_factory=dict,
        description="Optional transient actual dates (event_code -> date) for dry-run anchoring.",
    )
    recalculate: bool = True

    @field_validator("object_type")
    @classmethod
    def validate_object_type(cls, value: str) -> str:
        normalized = (value or "").strip().upper()
        if normalized not in {"PURCHASE_ORDER", "SHIPMENT"}:
            raise ValueError("object_type must be PURCHASE_ORDER or SHIPMENT.")
        return normalized


class TimelinePreviewItem(BaseModel):
    event_code: str
    event_name: str | None = None
    anchor_event_code: str | None = None
    anchor_event_name: str | None = None
    anchor_used_event_code: str | None = None
    anchor_used_event_name: str | None = None
    offset_minutes: int | None = None
    is_active: bool
    planned_date: datetime | None = None
    saved_planned_date: datetime | None = None
    planned_date_manual_override: bool = False
    baseline_date: datetime | None = None
    actual_date: datetime | None = None
    status: str | None = None
    status_reason: str | None = None
    timezone: str | None = None
    is_unsaved_change: bool = False


class TimelinePreviewResponse(BaseModel):
    object_type: str
    parent_id: int
    items: list[TimelinePreviewItem]


class TimelineSaveItem(BaseModel):
    event_code: str
    is_active: bool = True
    baseline_date: datetime | None = None
    planned_date: datetime | None = None
    planned_date_manual_override: bool | None = None
    actual_date: datetime | None = None
    status: str | None = None
    status_reason: str | None = None
    timezone: str | None = None


class TimelineSaveRequest(BaseModel):
    object_type: str = Field(description="Supported values: PURCHASE_ORDER, SHIPMENT")
    parent_id: int = Field(ge=1)
    events: list[TimelineSaveItem] = Field(default_factory=list)
    context_data: dict[str, Any] = Field(default_factory=dict)
    start_date: datetime | None = None
    recalculate: bool = False

    @field_validator("object_type")
    @classmethod
    def validate_object_type(cls, value: str) -> str:
        normalized = (value or "").strip().upper()
        if normalized not in {"PURCHASE_ORDER", "SHIPMENT"}:
            raise ValueError("object_type must be PURCHASE_ORDER or SHIPMENT.")
        return normalized


class TimelineSaveResponse(BaseModel):
    object_type: str
    parent_id: int
    deleted_count: int
    inserted_count: int
