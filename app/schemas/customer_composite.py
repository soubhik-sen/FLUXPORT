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


class CustomerPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[int] = None
    role_id: int = Field(alias="customer_group")
    company_id: Optional[int] = None
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    tax_registration_id: Optional[str] = Field(default=None, max_length=50)
    payment_terms_code: Optional[str] = Field(default=None, max_length=20)
    preferred_currency: str = Field(default="USD", max_length=3)
    is_active: bool = True
    is_verified: bool = False
    validity_to: date = Field(default=date(9999, 12, 31))


class CustomerFullSchema(BaseModel):
    address: AddressPayload
    customer: CustomerPayload
    is_edit_mode: bool = False


class AddressResponse(AddressPayload):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str


class CustomerResponse(CustomerPayload):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    customer_identifier: str
    addr_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str


class CustomerFullResponse(BaseModel):
    customer: CustomerResponse
    address: Optional[AddressResponse] = None
