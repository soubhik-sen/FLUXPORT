from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseSchema


class CompanyMasterBase(BaseModel):
    branch_code: str = Field(min_length=1, max_length=10)
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    tax_id: str = Field(min_length=1, max_length=50)
    is_active: bool = True
    addr_id: Optional[int] = None
    default_currency: str = Field(default="USD", max_length=5)


class CompanyMasterCreate(CompanyMasterBase):
    company_code: Optional[str] = Field(default=None, max_length=10)


class CompanyMasterUpdate(BaseModel):
    company_code: Optional[str] = Field(default=None, min_length=1, max_length=10)
    branch_code: Optional[str] = Field(default=None, min_length=1, max_length=10)
    legal_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    tax_id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    is_active: Optional[bool] = None
    addr_id: Optional[int] = None
    default_currency: Optional[str] = Field(default=None, max_length=5)


class CompanyMasterOut(CompanyMasterBase, BaseSchema):
    id: int
    company_code: str = Field(min_length=1, max_length=10)
    created_at: datetime
    updated_at: datetime
