from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from decimal import Decimal
from .base import BaseSchema

class POItemBase(BaseModel):
    item_number: int
    product_id: int
    status_id: int
    quantity: Decimal = Field(max_digits=15, decimal_places=3)
    unit_price: Decimal = Field(max_digits=15, decimal_places=2)
    line_total: Decimal = Field(max_digits=15, decimal_places=2)

class POItemCreate(POItemBase):
    pass

class POItem(POItemBase, BaseSchema):
    id: int
    po_header_id: int

class POHeaderBase(BaseModel):
    po_number: str
    type_id: int
    status_id: int
    purchase_org_id: int
    company_id: int
    vendor_id: int
    order_date: date
    currency: str = "USD"
    total_amount: Decimal = Decimal("0.00")

class POHeaderCreate(POHeaderBase):
    # Allows creating a PO with items in one request
    items: List[POItemCreate] = []

class POHeader(POHeaderBase, BaseSchema):
    id: int
    items: List[POItem] = []