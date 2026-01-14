from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCountryBase(BaseModel):
    user_id: int = Field(ge=1)
    country_code: str = Field(min_length=2, max_length=2)  # ISO-2


class UserCountryCreate(UserCountryBase):
    pass


class UserCountryUpdate(BaseModel):
    user_id: Optional[int] = Field(default=None, ge=1)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)


class UserCountryOut(UserCountryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
