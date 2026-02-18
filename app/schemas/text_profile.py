from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class RuntimeTextRowIn(BaseModel):
    text_type_id: int | None = Field(default=None, ge=1)
    text_type_code: str | None = Field(default=None, max_length=20)
    text_type_name: str | None = Field(default=None, max_length=100)
    language: str = Field(default="en", max_length=10)
    text_value: str = Field(default="", max_length=10000)
    is_editable: bool | None = None
    is_mandatory: bool | None = None
    source: str | None = None


class RuntimeTextRowOut(BaseModel):
    id: int
    source: str
    text_type_id: int
    text_type_code: str | None = None
    text_type_name: str | None = None
    language: str
    text_value: str
    is_editable: bool = True
    is_mandatory: bool = False
    is_user_edited: bool = False
    profile_id: int | None = None
    profile_version: int | None = None


class POTextProfileResolveRequest(BaseModel):
    type_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    company_id: int | None = Field(default=None, ge=1)
    vendor_id: int | None = Field(default=None, ge=1)
    forwarder_id: int | None = Field(default=None, ge=1)
    order_date: date | None = None
    currency: str | None = Field(default=None, max_length=3)
    locale_override_language: str | None = Field(default=None, max_length=10)
    locale_override_country: str | None = Field(default=None, max_length=8)


class ShipmentTextProfileResolveRequest(BaseModel):
    type_id: int | None = Field(default=None, ge=1)
    status_id: int | None = Field(default=None, ge=1)
    mode_id: int | None = Field(default=None, ge=1)
    carrier_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    company_id: int | None = Field(default=None, ge=1)
    vendor_id: int | None = Field(default=None, ge=1)
    forwarder_id: int | None = Field(default=None, ge=1)
    estimated_departure: date | None = None
    estimated_arrival: date | None = None
    locale_override_language: str | None = Field(default=None, max_length=10)
    locale_override_country: str | None = Field(default=None, max_length=8)


class TextProfileResolveResponse(BaseModel):
    profile_id: int | None = None
    profile_name: str | None = None
    profile_version: int | None = None
    language: str = "en"
    country_code: str | None = None
    source: str
    texts: list[RuntimeTextRowOut] = Field(default_factory=list)


class RuntimeTextsUpdateRequest(BaseModel):
    profile_id: int | None = Field(default=None, ge=1)
    profile_version: int | None = Field(default=None, ge=1)
    texts: list[RuntimeTextRowIn] = Field(default_factory=list)


class RuntimeTextsUpdateResponse(BaseModel):
    profile_id: int | None = None
    profile_version: int | None = None
    texts: list[RuntimeTextRowOut] = Field(default_factory=list)


def runtime_row_to_dict(row: RuntimeTextRowIn | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, RuntimeTextRowIn):
        return row.model_dump()
    return dict(row)
