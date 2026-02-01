from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SupplierBase(BaseModel):
    supplier_id: int = Field(ge=1)
    branch_id: int = Field(ge=1)
    addr_id: Optional[int] = Field(default=None, ge=1)

    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    deletion_indicator: bool = False


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    supplier_id: Optional[int] = Field(default=None, ge=1)
    branch_id: Optional[int] = Field(default=None, ge=1)
    addr_id: Optional[int] = Field(default=None, ge=1)

    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    deletion_indicator: Optional[bool] = None


class SupplierOut(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
