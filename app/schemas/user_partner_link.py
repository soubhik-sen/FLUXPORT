from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseSchema


class UserPartnerLinkBase(BaseModel):
    user_email: str
    partner_id: int = Field(ge=1)
    deletion_indicator: bool = False


class UserPartnerLinkCreate(UserPartnerLinkBase):
    pass


class UserPartnerLinkUpdate(BaseModel):
    user_email: Optional[str] = None
    partner_id: Optional[int] = Field(default=None, ge=1)
    deletion_indicator: Optional[bool] = None


class UserPartnerLinkOut(UserPartnerLinkBase, BaseSchema):
    id: int
    partner_name: Optional[str] = None
    user_name: Optional[str] = None


class UserSearchResult(BaseModel):
    email: str
    name: str
    id: Optional[int] = None


class PartnerSearchResult(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
