from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseSchema


class UserCustomerLinkBase(BaseModel):
    user_email: str
    customer_id: int = Field(ge=1)
    deletion_indicator: bool = False


class UserCustomerLinkCreate(UserCustomerLinkBase):
    pass


class UserCustomerLinkUpdate(BaseModel):
    user_email: Optional[str] = None
    customer_id: Optional[int] = Field(default=None, ge=1)
    deletion_indicator: Optional[bool] = None


class UserCustomerLinkOut(UserCustomerLinkBase, BaseSchema):
    id: int
    customer_name: Optional[str] = None
    user_name: Optional[str] = None


class UserSearchResult(BaseModel):
    email: str
    name: str
    id: Optional[int] = None


class CustomerSearchResult(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
