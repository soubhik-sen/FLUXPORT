from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)


class RoleOut(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
