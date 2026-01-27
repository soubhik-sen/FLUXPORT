from pydantic import BaseModel
from typing import Optional

class NumberRangeBase(BaseModel):
    doc_category: str
    doc_type_id: int
    prefix: str
    current_value: int = 0
    padding: int = 5
    include_year: bool = False
    is_active: bool = True

class NumberRangeCreate(NumberRangeBase):
    pass

class NumberRangeUpdate(BaseModel):
    prefix: Optional[str] = None
    current_value: Optional[int] = None
    padding: Optional[int] = None
    include_year: Optional[bool] = None
    is_active: Optional[bool] = None

class NumberRangeResponse(NumberRangeBase):
    id: int

    class Config:
        from_attributes = True