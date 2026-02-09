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
    forwarder_id: Optional[int] = None
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


class POWorkspaceHeader(BaseModel):
    id: int
    po_number: str
    po_type: Optional[str] = None
    po_status: Optional[str] = None
    purchase_org: Optional[str] = None
    company_name: Optional[str] = None
    vendor_name: Optional[str] = None
    forwarder_name: Optional[str] = None
    order_date: date
    currency: str
    total_amount: Decimal = Field(max_digits=15, decimal_places=2)
    created_by: Optional[str] = None
    last_changed_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class POWorkspaceItem(BaseModel):
    po_item_id: int
    item_number: int
    product_id: Optional[int] = None
    sku: Optional[str] = None
    product_description: Optional[str] = None
    uom_code: Optional[str] = None
    item_status: Optional[str] = None
    quantity: Decimal = Field(max_digits=15, decimal_places=3)
    unit_price: Decimal = Field(max_digits=15, decimal_places=2)
    line_total: Decimal = Field(max_digits=15, decimal_places=2)


class POWorkspaceSchedule(BaseModel):
    po_schedule_line_id: int
    po_item_id: int
    item_number: int
    schedule_number: int
    quantity: Decimal = Field(max_digits=15, decimal_places=3)
    received_qty: Decimal = Field(max_digits=15, decimal_places=3)
    delivery_date: date
    shipment_header_id: Optional[int] = None
    shipment_number: Optional[str] = None


class POWorkspaceText(BaseModel):
    id: int
    source: str
    text_type: Optional[str] = None
    language: Optional[str] = None
    text_value: str
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class POWorkspaceDocument(BaseModel):
    id: int
    document_type: Optional[str] = None
    file_name: str
    file_extension: str
    file_size_kb: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    uploaded_by_id: Optional[int] = None


class POWorkspaceCharge(BaseModel):
    charge_code: str
    charge_name: str
    amount: Decimal = Field(max_digits=15, decimal_places=2)
    currency: str
    source: str


class POWorkspaceResponse(BaseModel):
    header: POWorkspaceHeader
    items: List[POWorkspaceItem]
    schedules: List[POWorkspaceSchedule]
    texts: List[POWorkspaceText]
    documents: List[POWorkspaceDocument]
    charges: List[POWorkspaceCharge]


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


class POScheduleMergeLine(BaseModel):
    source_schedule_line_id: int
    target_schedule_line_id: int


class POScheduleMergeRequest(BaseModel):
    merges: List[POScheduleMergeLine]
