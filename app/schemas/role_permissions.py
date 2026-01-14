from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RolePermissionBase(BaseModel):
    role_id: int = Field(ge=1)
    permission_id: int = Field(ge=1)
    role_name: str = Field(min_length=1, max_length=80)


class RolePermissionCreate(RolePermissionBase):
    pass


class RolePermissionUpdate(BaseModel):
    role_id: Optional[int] = Field(default=None, ge=1)
    permission_id: Optional[int] = Field(default=None, ge=1)
    role_name: Optional[str] = Field(default=None, min_length=1, max_length=80)


class RolePermissionOut(RolePermissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
