from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserAttributeBase(BaseModel):
    user_id: int = Field(ge=1)
    key: str = Field(min_length=1, max_length=80)
    value: Optional[str] = None


class UserAttributeCreate(UserAttributeBase):
    pass


class UserAttributeUpdate(BaseModel):
    user_id: Optional[int] = Field(default=None, ge=1)
    key: Optional[str] = Field(default=None, min_length=1, max_length=80)
    value: Optional[str] = None


class UserAttributeOut(UserAttributeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
