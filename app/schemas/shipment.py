from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from .base import BaseSchema

class ShipmentItemBase(BaseModel):
    po_item_id: int
    po_schedule_line_id: Optional[int] = None
    po_number: Optional[str] = None
    predecessor_doc: Optional[str] = None
    predecessor_item_no: Optional[int] = None
    shipment_item_number: Optional[int] = None
    shipped_qty: Decimal = Field(max_digits=15, decimal_places=3)
    package_id: Optional[str] = None
    gross_weight: Optional[Decimal] = None

class ShipmentItemCreate(ShipmentItemBase):
    pass

class ShipmentHeaderBase(BaseModel):
    shipment_number: Optional[str] = None
    external_reference: Optional[str] = None
    type_id: Optional[int] = None
    status_id: int
    mode_id: int
    carrier_id: int
    pol_port_id: Optional[int] = None
    pod_port_id: Optional[int] = None
    master_bill_lading: Optional[str] = None
    estimated_departure: Optional[date] = None
    estimated_arrival: Optional[date] = None
    created_by: str
    last_changed_by: Optional[str] = None

class ShipmentHeaderCreate(ShipmentHeaderBase):
    items: List[ShipmentItemCreate]

class ShipmentHeader(ShipmentHeaderBase, BaseSchema):
    id: int
    items: List[ShipmentItemBase] = []
    created_at: datetime
    updated_at: datetime


class ShipmentHeaderSummary(BaseModel):
    id: int
    shipment_number: str
    status_id: int
    estimated_departure: Optional[date] = None
    estimated_arrival: Optional[date] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class ShipmentWorkspaceHeader(BaseModel):
    id: int
    shipment_number: str
    external_reference: Optional[str] = None
    shipment_type: Optional[str] = None
    shipment_status: Optional[str] = None
    transport_mode: Optional[str] = None
    carrier_code: Optional[str] = None
    carrier_name: Optional[str] = None
    pol_port: Optional[str] = None
    pod_port: Optional[str] = None
    master_bill_lading: Optional[str] = None
    estimated_departure: Optional[date] = None
    estimated_arrival: Optional[date] = None
    actual_arrival: Optional[date] = None
    created_by: Optional[str] = None
    last_changed_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ShipmentWorkspaceItem(BaseModel):
    shipment_item_id: int
    shipment_item_number: Optional[int] = None
    po_number: Optional[str] = None
    predecessor_doc: Optional[str] = None
    predecessor_item_no: Optional[int] = None
    schedule_line_no: Optional[int] = None
    shipped_qty: Decimal = Field(max_digits=15, decimal_places=3)
    package_id: Optional[str] = None
    gross_weight: Optional[Decimal] = None
    sku: Optional[str] = None
    product_description: Optional[str] = None
    vendor_name: Optional[str] = None
    forwarder_name: Optional[str] = None


class ShipmentWorkspaceMilestone(BaseModel):
    id: int
    milestone_code: Optional[str] = None
    milestone_name: Optional[str] = None
    event_datetime: datetime
    location: Optional[str] = None
    notes: Optional[str] = None


class ShipmentWorkspaceDocument(BaseModel):
    id: int
    document_type: Optional[str] = None
    file_name: str
    file_extension: str
    file_size_kb: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    uploaded_by_id: Optional[int] = None


class ShipmentWorkspaceContainer(BaseModel):
    id: int
    container_code: Optional[str] = None
    container_name: Optional[str] = None
    container_number: str
    seal_number: Optional[str] = None


class ShipmentWorkspaceResponse(BaseModel):
    header: ShipmentWorkspaceHeader
    items: List[ShipmentWorkspaceItem]
    milestones: List[ShipmentWorkspaceMilestone]
    documents: List[ShipmentWorkspaceDocument]
    containers: List[ShipmentWorkspaceContainer]


class ShipmentSplitLine(BaseModel):
    schedule_line_id: int
    qty: Decimal = Field(max_digits=15, decimal_places=3)
    split_line_id: Optional[str] = None
    schedule_line_no: Optional[int] = None
    ship: Optional[bool] = True

    @field_validator('qty', mode='before')
    @classmethod
    def _quantize_qty(cls, value):
        if value is None:
            return value
        try:
            dec = value if isinstance(value, Decimal) else Decimal(str(value))
        except Exception:
            return value
        return dec.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


class ShipmentFromScheduleLinesRequest(BaseModel):
    schedule_line_ids: Optional[List[int]] = None
    lines: Optional[List[ShipmentSplitLine]] = None
