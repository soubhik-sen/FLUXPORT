from sqlalchemy import String, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.doc_lookups import DocumentTypeLookup

class DocumentAttachment(Base):
    """
    Stores metadata and paths for uploaded files.
    Can be linked to Shipments, POs, or Partners.
    """
    __tablename__ = "document_attachment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # FK to Document Type Lookup
    type_id: Mapped[int] = mapped_column(ForeignKey("document_type_lookup.id"), nullable=False)
    
    # File Storage Info
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False) # S3 Bucket URL or local path
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False) # .pdf, .jpg
    file_size_kb: Mapped[int] = mapped_column(Integer, nullable=True)

    # Contextual Links (Optional FKs for traceability)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey("shipment_header.id"), nullable=True)
    po_header_id: Mapped[int | None] = mapped_column(ForeignKey("po_header.id"), nullable=True)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partner_master.id"), nullable=True)

    # Relationships
    doc_type: Mapped["DocumentTypeLookup"] = relationship("DocumentTypeLookup")

    uploaded_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    # User ID who uploaded (assuming you have a User model)
    uploaded_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True) 

    def __repr__(self) -> str:
        return f"<Document(name='{self.file_name}', type='{self.type_id}')>"