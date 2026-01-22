from sqlalchemy import Column, Integer, ForeignKey, Numeric, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # These imports ONLY happen for the IDE/Linter
    # They are completely ignored by Python at runtime
    from app.models.purchase_order import PurchaseOrderItem
    from app.models.shipment import ShipmentHeader, ShipmentItem

# CRITICAL: Do NOT import PurchaseOrderItem, ShipmentHeader, or ShipmentItem 
# at the top of this file. Use string literals in relationship definitions.

class POScheduleLine(Base):
    """
    Enterprise Schedule Line: Splits a PO Item into specific delivery dates.
    Each Schedule Line is linked to exactly one Shipment Header (1:N).
    """
    __tablename__ = "po_schedule_line"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Link to the Commercial Item (po_item table)
    po_item_id: Mapped[int] = mapped_column(ForeignKey("po_item.id"), nullable=False)
    
    # Link to Logistics Execution (shipment_header table)
    shipment_header_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipment_header.id"), 
        nullable=True
    )
    
    schedule_number: Mapped[int] = mapped_column(nullable=False, default=1)
    
    # Quantities
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    received_qty: Mapped[float] = mapped_column(Numeric(15, 3), default=0.000)
    
    # Dates
    delivery_date: Mapped[object] = mapped_column(Date, nullable=False)

    # Relationships using String Literals to avoid Circular Imports
    item: Mapped["PurchaseOrderItem"] = relationship(
        "PurchaseOrderItem", 
        back_populates="schedules"
    )
    
    shipment: Mapped["ShipmentHeader"] = relationship(
        "ShipmentHeader", 
        back_populates="schedule_lines"
    )

    # ShipmentItems point here to verify packing/actuals
    shipment_items: Mapped[list["ShipmentItem"]] = relationship(
        "ShipmentItem", 
        back_populates="schedule_line"
    )

    def __repr__(self) -> str:
        return f"<POScheduleLine(item_id={self.po_item_id}, qty={self.quantity}, shipment_id={self.shipment_header_id})>"