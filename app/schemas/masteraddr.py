from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime


class MasterAddrBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    # this maps to DB column "type"
    addr_type: Optional[str] = Field(default=None, max_length=50)

    country: Optional[str] = Field(default=None, max_length=2)  # ISO-2 like "ES"
    region: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    zip: Optional[str] = Field(default=None, max_length=20)

    street: Optional[str] = Field(default=None, max_length=200)
    housenumber: Optional[str] = Field(default=None, max_length=20)

    phone1: Optional[str] = Field(default=None, max_length=30)
    phone2: Optional[str] = Field(default=None, max_length=30)
    emailid: Optional[EmailStr] = None

    timezone: Optional[str] = Field(default=None, max_length=64)  # e.g. "Europe/Madrid"

    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    deletion_indicator: bool = False


class MasterAddrCreate(MasterAddrBase):
    pass


class MasterAddrUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    addr_type: Optional[str] = Field(default=None, max_length=50)

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

    deletion_indicator: Optional[bool] = None


class MasterAddrOut(MasterAddrBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_changed_by: str
