from sqlalchemy import String, ForeignKey, DateTime, func, Date, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# Maintaining required lookup imports
from app.models.po_lookups import (
    PurchaseOrderStatusLookup, 
    PurchaseOrderTypeLookup, 
    PurchaseOrgLookup,
    PurchaseOrderItemStatusLookup
)

# CRITICAL: We DO NOT import POScheduleLine here to avoid circular dependencies.
# SQLAlchemy will resolve the string "POScheduleLine" at runtime.
from app.models.product_master import ProductMaster

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # These imports ONLY happen for the IDE/Linter
    # They are completely ignored by Python at runtime
    from app.models.po_schedule_line import POScheduleLine

class PurchaseOrderHeader(Base):
    """
    Main Commercial Document. 
    References Lookup tables for Status, Document Type, and Purchase Org.
    """
    __tablename__ = "po_header"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    po_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    
    # FKs to Lookups
    type_id: Mapped[int] = mapped_column(ForeignKey("po_type_lookup.id"), nullable=False)
    status_id: Mapped[int] = mapped_column(ForeignKey("po_status_lookup.id"), nullable=False)
    purchase_org_id: Mapped[int] = mapped_column(ForeignKey("purchase_org_lookup.id"), nullable=False)
    
    # FKs to Master Data
    company_id: Mapped[int] = mapped_column(ForeignKey("company_master.id"), nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("partner_master.id"), nullable=False)
    
    order_date: Mapped[object] = mapped_column(Date, server_default=func.current_date())
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0.00)

    # Relationships
    purchase_org: Mapped["PurchaseOrgLookup"] = relationship("PurchaseOrgLookup")
    doc_type: Mapped["PurchaseOrderTypeLookup"] = relationship("PurchaseOrderTypeLookup")
    status: Mapped["PurchaseOrderStatusLookup"] = relationship("PurchaseOrderStatusLookup")
    
    # Relationship to Items using string reference
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem", 
        back_populates="header",
        cascade="all, delete-orphan"
    )

    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class PurchaseOrderItem(Base):
    """
    Line item details for a Purchase Order.
    Links products to the header with specific quantities and statuses.
    """
    __tablename__ = "po_item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    po_header_id: Mapped[int] = mapped_column(ForeignKey("po_header.id"), nullable=False)
    
    item_number: Mapped[int] = mapped_column(nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product_master.id"), nullable=False)
    status_id: Mapped[int] = mapped_column(ForeignKey("po_item_status_lookup.id"), nullable=False)
    
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    split_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)

    # Relationships
    header: Mapped["PurchaseOrderHeader"] = relationship("PurchaseOrderHeader", back_populates="items")
    product: Mapped["ProductMaster"] = relationship("ProductMaster")
    status: Mapped["PurchaseOrderItemStatusLookup"] = relationship("PurchaseOrderItemStatusLookup")

    # FIX: Link to POScheduleLine using string literal to prevent Circular Import
    schedules: Mapped[list["POScheduleLine"]] = relationship(
        "POScheduleLine", 
        back_populates="item", 
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<POItem(header_id={self.po_header_id}, item={self.item_number})>"