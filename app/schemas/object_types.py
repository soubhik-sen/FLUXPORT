from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ObjectTypeBase(BaseModel):
    object_type: str = Field(min_length=1, max_length=10)
    object_description: str = Field(min_length=1, max_length=255)


class ObjectTypeCreate(ObjectTypeBase):
    pass


class ObjectTypeUpdate(BaseModel):
    # PK changes not recommended, but allowed if you want
    object_type: Optional[str] = Field(default=None, min_length=1, max_length=10)
    object_description: Optional[str] = Field(default=None, min_length=1, max_length=255)


class ObjectTypeOut(ObjectTypeBase):
    model_config = ConfigDict(from_attributes=True)
