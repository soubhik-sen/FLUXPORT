from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserDepartmentBase(BaseModel):
    user_id: int = Field(ge=1)
    department: str = Field(min_length=1, max_length=80)


class UserDepartmentCreate(UserDepartmentBase):
    pass


class UserDepartmentUpdate(BaseModel):
    user_id: Optional[int] = Field(default=None, ge=1)
    department: Optional[str] = Field(default=None, min_length=1, max_length=80)


class UserDepartmentOut(UserDepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
