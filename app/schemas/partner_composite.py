from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AddressPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    addr_type: str = Field(min_length=1, max_length=50)
    country: Optional[str] = Field(default=None, max_length=2)
    region: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    zip: Optional[str] = Field(default=None, max_length=20)
    street: Optional[str] = Field(default=None, max_length=200)
    housenumber: Optional[str] = Field(default=None, max_length=20)
    phone1: Optional[str] = Field(default=None, max_length=30)
    phone2: Optional[str] = Field(default=None, max_length=30)
    emailid: Optional[EmailStr] = None
    timezone: Optional[str] = Field(default=None, max_length=64)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    deletion_indicator: bool = False


class PartnerPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[int] = None
    role_id: int = Field(alias="partner_role")
    partner_identifier: Optional[str] = Field(default=None, min_length=1, max_length=20)
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    tax_registration_id: Optional[str] = Field(default=None, max_length=50)
    payment_terms_code: Optional[str] = Field(default=None, max_length=20)
    preferred_currency: str = Field(default="USD", max_length=3)
    is_active: bool = True
    is_verified: bool = False


class PartnerFullSchema(BaseModel):
    address: AddressPayload
    partner: PartnerPayload
    is_edit_mode: bool = False


class AddressResponse(AddressPayload):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str


class PartnerResponse(PartnerPayload):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    partner_identifier: str
    addr_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class PartnerFullResponse(BaseModel):
    partner: PartnerResponse
    address: Optional[AddressResponse] = None
