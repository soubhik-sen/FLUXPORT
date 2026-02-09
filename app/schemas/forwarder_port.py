from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseSchema


class ForwarderPortBase(BaseModel):
    forwarder_id: int = Field(ge=1)
    port_id: int = Field(ge=1)
    deletion_indicator: bool = False


class ForwarderPortCreate(ForwarderPortBase):
    pass


class ForwarderPortUpdate(BaseModel):
    forwarder_id: Optional[int] = Field(default=None, ge=1)
    port_id: Optional[int] = Field(default=None, ge=1)
    deletion_indicator: Optional[bool] = None


class ForwarderPortOut(ForwarderPortBase, BaseSchema):
    id: int
    forwarder_name: Optional[str] = None
    port_label: Optional[str] = None


class PortOption(BaseModel):
    id: int
    code: str
    name: str
    country: str
    label: str
