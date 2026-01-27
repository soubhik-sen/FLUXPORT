from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .base import BaseSchema


class DocumentAttachmentBase(BaseModel):
    type_id: int
    file_name: str
    file_path: str
    file_extension: str
    file_size_kb: Optional[int] = None
    shipment_id: Optional[int] = None
    po_header_id: Optional[int] = None
    partner_id: Optional[int] = None
    created_by: str
    last_changed_by: Optional[str] = None


class DocumentAttachmentCreate(DocumentAttachmentBase):
    pass


class DocumentAttachment(DocumentAttachmentBase, BaseSchema):
    id: int
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
