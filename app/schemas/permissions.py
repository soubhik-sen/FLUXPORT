from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    # action technical key (from domains where domain_name="ACTION")
    action_key: str = Field(min_length=1, max_length=40)

    # object type code (PK from object_types)
    object_type: str = Field(min_length=1, max_length=10)


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    action_key: Optional[str] = Field(default=None, min_length=1, max_length=40)
    object_type: Optional[str] = Field(default=None, min_length=1, max_length=10)


class PermissionOut(PermissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
