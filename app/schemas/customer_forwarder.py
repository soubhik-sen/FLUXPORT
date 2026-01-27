from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseSchema


class CustomerForwarderBase(BaseModel):
    customer_id: int = Field(ge=1)
    forwarder_id: int = Field(ge=1)
    deletion_indicator: bool = False


class CustomerForwarderCreate(CustomerForwarderBase):
    pass


class CustomerForwarderUpdate(BaseModel):
    customer_id: Optional[int] = Field(default=None, ge=1)
    forwarder_id: Optional[int] = Field(default=None, ge=1)
    deletion_indicator: Optional[bool] = None


class CustomerForwarderOut(CustomerForwarderBase, BaseSchema):
    id: int
    customer_name: Optional[str] = None
    forwarder_name: Optional[str] = None


class SearchResult(BaseModel):
    id: int
    name: str
