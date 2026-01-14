from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRoleBase(BaseModel):
    user_id: int = Field(ge=1)
    role_id: int = Field(ge=1)


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleUpdate(BaseModel):
    user_id: Optional[int] = Field(default=None, ge=1)
    role_id: Optional[int] = Field(default=None, ge=1)


class UserRoleOut(UserRoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
