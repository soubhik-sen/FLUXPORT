from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DomainBase(BaseModel):
    domain_name: str = Field(min_length=1, max_length=80)
    technical_key: str = Field(min_length=1, max_length=40)
    display_label: Optional[str] = Field(default=None, max_length=120)
    is_active: bool = True


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    domain_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    technical_key: Optional[str] = Field(default=None, min_length=1, max_length=40)
    display_label: Optional[str] = Field(default=None, max_length=120)
    is_active: Optional[bool] = None


class DomainOut(DomainBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
