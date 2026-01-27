from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseSchema


class PartnerTypeBase(BaseModel):
    role_code: str = Field(min_length=1, max_length=30)
    role_name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True


class PartnerTypeCreate(PartnerTypeBase):
    pass


class PartnerTypeUpdate(BaseModel):
    role_code: Optional[str] = Field(default=None, min_length=1, max_length=30)
    role_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class PartnerTypeOut(PartnerTypeBase, BaseSchema):
    id: int
    created_at: datetime
