from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ForwarderBase(BaseModel):
    forwarder_id: int = Field(ge=1)
    branch_id: int = Field(ge=1)

    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    deletion_indicator: bool = False


class ForwarderCreate(ForwarderBase):
    pass


class ForwarderUpdate(BaseModel):
    forwarder_id: Optional[int] = Field(default=None, ge=1)
    branch_id: Optional[int] = Field(default=None, ge=1)

    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    deletion_indicator: Optional[bool] = None


class ForwarderOut(ForwarderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
