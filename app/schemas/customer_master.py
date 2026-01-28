from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseSchema


class CustomerMasterBase(BaseModel):
    customer_identifier: str = Field(min_length=1, max_length=20)
    role_id: int
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    tax_registration_id: Optional[str] = Field(default=None, max_length=50)
    payment_terms_code: Optional[str] = Field(default=None, max_length=20)
    preferred_currency: str = Field(default="USD", max_length=3)
    validity_to: date = Field(default=date(9999, 12, 31))
    is_active: bool = True
    is_verified: bool = False
    addr_id: Optional[int] = None


class CustomerMasterCreate(CustomerMasterBase):
    pass


class CustomerMasterUpdate(BaseModel):
    customer_identifier: Optional[str] = Field(default=None, min_length=1, max_length=20)
    role_id: Optional[int] = None
    legal_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    tax_registration_id: Optional[str] = Field(default=None, max_length=50)
    payment_terms_code: Optional[str] = Field(default=None, max_length=20)
    preferred_currency: Optional[str] = Field(default=None, max_length=3)
    validity_to: Optional[date] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    addr_id: Optional[int] = None


class CustomerMasterOut(CustomerMasterBase, BaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str
