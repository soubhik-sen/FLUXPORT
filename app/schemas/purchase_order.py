from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from .base import BaseSchema

class POItemBase(BaseModel):
    item_number: int
    product_id: int
    status_id: int
    quantity: Decimal = Field(max_digits=15, decimal_places=3)
    unit_price: Decimal = Field(max_digits=15, decimal_places=2)
    line_total: Decimal = Field(max_digits=15, decimal_places=2)

class POScheduleLineBase(BaseModel):
    schedule_number: Optional[int] = None
    quantity: Decimal = Field(max_digits=15, decimal_places=3)
    delivery_date: date

class POScheduleLineCreate(POScheduleLineBase):
    pass

class POScheduleLine(POScheduleLineBase, BaseSchema):
    id: int
    po_item_id: int

class POItemCreate(POItemBase):
    schedules: List[POScheduleLineCreate] = []

class POItem(POItemBase, BaseSchema):
    id: int
    po_header_id: int
    schedules: List[POScheduleLine] = []

class POHeaderBase(BaseModel):
    po_number: Optional[str] = None
    type_id: int
    status_id: int
    purchase_org_id: int
    company_id: int
    vendor_id: int
    order_date: date
    currency: str = "USD"
    total_amount: Decimal = Decimal("0.00")
    created_by: str
    last_changed_by: Optional[str] = None

class POHeaderCreate(POHeaderBase):
    # Allows creating a PO with items in one request
    items: List[POItemCreate] = []

class POHeader(POHeaderBase, BaseSchema):
    id: int
    items: List[POItem] = []
    created_at: datetime
    updated_at: datetime


class POInitItem(BaseModel):
    id: int
    code: str
    name: str


class POInitializationResponse(BaseModel):
    po_types: List[POInitItem]
    statuses: List[POInitItem]
    purchase_orgs: List[POInitItem]
    companies: List[POInitItem]
    vendors: List[POInitItem]
