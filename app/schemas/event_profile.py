from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.base import BaseSchema


class EventProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    timezone: Optional[str] = Field(default=None, max_length=64)


class EventProfileCreate(EventProfileBase):
    pass


class EventProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    timezone: Optional[str] = Field(default=None, max_length=64)


class EventProfileOut(EventProfileBase, BaseSchema):
    id: int
    profile_version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str


class ProfileEventMapBase(BaseModel):
    profile_id: int = Field(ge=1)
    event_code: str = Field(min_length=1, max_length=30)
    inclusion_rule_id: Optional[str] = Field(default=None, max_length=120)
    anchor_event_code: Optional[str] = Field(default=None, max_length=30)
    sequence: int = 0
    offset_days: int = 0
    is_mandatory: bool = True


class ProfileEventMapCreate(ProfileEventMapBase):
    pass


class ProfileEventMapUpdate(BaseModel):
    profile_id: Optional[int] = Field(default=None, ge=1)
    event_code: Optional[str] = Field(default=None, min_length=1, max_length=30)
    inclusion_rule_id: Optional[str] = Field(default=None, max_length=120)
    anchor_event_code: Optional[str] = Field(default=None, max_length=30)
    sequence: Optional[int] = None
    offset_days: Optional[int] = None
    is_mandatory: Optional[bool] = None


class ProfileEventMapOut(ProfileEventMapBase, BaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str
    profile_name: Optional[str] = None
    event_name: Optional[str] = None
    anchor_event_name: Optional[str] = None


EventStatus = Literal["PLANNED", "COMPLETED", "DELAYED"]


class EventInstanceBase(BaseModel):
    parent_id: int = Field(ge=1)
    po_header_id: Optional[int] = Field(default=None, ge=1)
    shipment_header_id: Optional[int] = Field(default=None, ge=1)
    po_number: Optional[str] = Field(default=None, max_length=40)
    shipment_number: Optional[str] = Field(default=None, max_length=40)
    profile_id: Optional[int] = Field(default=None, ge=1)
    profile_version: Optional[int] = None
    event_code: str = Field(min_length=1, max_length=30)
    baseline_date: Optional[datetime] = None
    planned_date: Optional[datetime] = None
    planned_date_manual_override: bool = False
    status_reason: Optional[str] = Field(default=None, max_length=255)
    timezone: Optional[str] = Field(default=None, max_length=64)
    actual_date: Optional[datetime] = None
    status: EventStatus = "PLANNED"

    @model_validator(mode="after")
    def validate_single_parent(self):
        has_po = self.po_header_id is not None
        has_shipment = self.shipment_header_id is not None
        if has_po == has_shipment:
            raise ValueError("Provide exactly one of po_header_id or shipment_header_id.")
        if has_po and self.parent_id != self.po_header_id:
            raise ValueError("parent_id must match po_header_id when PO parent is used.")
        if has_shipment and self.parent_id != self.shipment_header_id:
            raise ValueError("parent_id must match shipment_header_id when shipment parent is used.")
        return self


class EventInstanceCreate(EventInstanceBase):
    pass


class EventInstanceUpdate(BaseModel):
    parent_id: Optional[int] = Field(default=None, ge=1)
    po_header_id: Optional[int] = Field(default=None, ge=1)
    shipment_header_id: Optional[int] = Field(default=None, ge=1)
    profile_id: Optional[int] = Field(default=None, ge=1)
    profile_version: Optional[int] = None
    event_code: Optional[str] = Field(default=None, min_length=1, max_length=30)
    baseline_date: Optional[datetime] = None
    planned_date: Optional[datetime] = None
    planned_date_manual_override: Optional[bool] = None
    status_reason: Optional[str] = Field(default=None, max_length=255)
    timezone: Optional[str] = Field(default=None, max_length=64)
    actual_date: Optional[datetime] = None
    status: Optional[EventStatus] = None


class EventInstanceOut(EventInstanceBase, BaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str
    event_name: Optional[str] = None
