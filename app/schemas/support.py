from pydantic import BaseModel
from typing import Optional
from .base import BaseSchema

class TextMasterBase(BaseModel):
    type_id: int
    content: str
    po_header_id: Optional[int] = None
    shipment_id: Optional[int] = None
    partner_id: Optional[int] = None
    product_id: Optional[int] = None

class TextMasterCreate(TextMasterBase):
    pass

class TextMaster(TextMasterBase, BaseSchema):
    id: int