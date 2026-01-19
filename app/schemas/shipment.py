from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from .base import BaseSchema

class ShipmentItemBase(BaseModel):
    po_item_id: int
    shipped_qty: Decimal = Field(max_digits=15, decimal_places=3)
    package_id: Optional[str] = None
    gross_weight: Optional[Decimal] = None

class ShipmentItemCreate(ShipmentItemBase):
    pass

class ShipmentHeaderBase(BaseModel):
    shipment_number: str
    status_id: int
    mode_id: int
    carrier_id: int
    master_bill_lading: Optional[str] = None
    estimated_departure: Optional[date] = None
    estimated_arrival: Optional[date] = None

class ShipmentHeaderCreate(ShipmentHeaderBase):
    items: List[ShipmentItemCreate]

class ShipmentHeader(ShipmentHeaderBase, BaseSchema):
    id: int
    items: List[ShipmentItemBase] = []
    created_at: datetime