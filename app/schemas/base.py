from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class LookupBase(BaseSchema):
    id: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(
        from_attributes=True,      # Allows reading from SQLAlchemy objects
        populate_by_name=True,     # Allows code="AIR" or mode_code="AIR"
        alias_generator=None,       # Keeps our manual Field aliases active
        serialize_by_alias=True
    )