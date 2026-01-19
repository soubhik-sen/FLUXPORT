from sqlalchemy import String, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.text_lookups import TextTypeLookup

class TextMaster(Base):
    """
    Generic text repository for instructions and notes.
    Linked to POs, Shipments, or Partners.
    """
    __tablename__ = "text_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # FK to Text Type
    type_id: Mapped[int] = mapped_column(ForeignKey("text_type_lookup.id"), nullable=False)
    
    # The actual content (using Text for unlimited length)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Contextual Links (Where does this text belong?)
    po_header_id: Mapped[int | None] = mapped_column(ForeignKey("po_header.id"), nullable=True)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey("shipment_header.id"), nullable=True)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partner_master.id"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_master.id"), nullable=True)

    # Relationships
    text_type: Mapped["TextT" \
    "ypeLookup"] = relationship("TextTypeLookup")

    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<TextMaster(id={self.id}, type='{self.type_id}')>"