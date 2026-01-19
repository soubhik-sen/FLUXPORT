from sqlalchemy import Numeric, String, ForeignKey, DateTime, func, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.logistics_lookups import ContainerTypeLookup, MilestoneTypeLookup, ShipmentStatusLookup, TransportModeLookup
from app.models.partner_master import PartnerMaster
from app.models.purchase_order import PurchaseOrderItem

class ShipmentItem(Base):
    """
    The 'Packing List' detail. 
    Links physical shipment lines to commercial PO lines.
    """
    __tablename__ = "shipment_item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shipment_header_id: Mapped[int] = mapped_column(ForeignKey("shipment_header.id"), nullable=False)
    
    # Link to the specific line in a PO
    po_item_id: Mapped[int] = mapped_column(ForeignKey("po_item.id"), nullable=False)
    
    # Logistics-specific quantity (e.g., shipping 50 out of 100 ordered)
    shipped_qty: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    
    # Physical packing details
    package_id: Mapped[str | None] = mapped_column(String(50), nullable=True) # e.g., Box ID
    gross_weight: Mapped[float | None] = mapped_column(Numeric(15, 3), nullable=True)

    # Relationships
    header: Mapped["ShipmentHeader"] = relationship("ShipmentHeader", back_populates="items")
    po_item: Mapped["PurchaseOrderItem"] = relationship("PurchaseOrderItem")

    def __repr__(self) -> str:
        return f"<ShipmentItem(shipment={self.shipment_header_id}, po_item={self.po_item_id})>"

class ShipmentHeader(Base):
    """
    Tracking the physical movement of goods.
    Links to a Carrier (Partner) and tracks status/mode via Lookups.
    """
    __tablename__ = "shipment_header"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shipment_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    
    # FKs to Lookups
    status_id: Mapped[int] = mapped_column(ForeignKey("shipment_status_lookup.id"), nullable=False)
    mode_id: Mapped[int] = mapped_column(ForeignKey("transport_mode_lookup.id"), nullable=False)
    
    # FKs to Master Data
    carrier_id: Mapped[int] = mapped_column(ForeignKey("partner_master.id"), nullable=False)
    
    # Logistics Details
    master_bill_lading: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_departure: Mapped[object | None] = mapped_column(Date, nullable=True)
    estimated_arrival: Mapped[object | None] = mapped_column(Date, nullable=True)
    actual_arrival: Mapped[object | None] = mapped_column(Date, nullable=True)

    # Relationships
    status: Mapped["ShipmentStatusLookup"] = relationship("ShipmentStatusLookup")
    transport_mode: Mapped["TransportModeLookup"] = relationship("TransportModeLookup")
    carrier: Mapped["PartnerMaster"] = relationship("PartnerMaster")

    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    items: Mapped[list["ShipmentItem"]] = relationship("ShipmentItem", back_populates="header")
    milestones = relationship("ShipmentMilestone", back_populates="header", cascade="all, delete-orphan")
    containers = relationship("ShipmentContainer", back_populates="header", cascade="all, delete-orphan")

class ShipmentMilestone(Base):
    """
    Tracks the actual history of a shipment's movement.
    """
    __tablename__ = "shipment_milestone"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shipment_header_id: Mapped[int] = mapped_column(ForeignKey("shipment_header.id"), nullable=False)
    
    # FK to Milestone Type Lookup
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestone_type_lookup.id"), nullable=False)
    
    event_datetime: Mapped[object] = mapped_column(DateTime, nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g., 'Singapore Port'
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    header: Mapped["ShipmentHeader"] = relationship("ShipmentHeader", back_populates="milestones")
    milestone_type: Mapped["MilestoneTypeLookup"] = relationship("MilestoneTypeLookup")

class ShipmentContainer(Base):
    """
    Tracks the physical equipment (Containers) linked to a shipment.
    """
    __tablename__ = "shipment_container"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shipment_header_id: Mapped[int] = mapped_column(ForeignKey("shipment_header.id"), nullable=False)
    
    # FK to Container Type Lookup
    container_type_id: Mapped[int] = mapped_column(ForeignKey("container_type_lookup.id"), nullable=False)
    
    container_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    seal_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    header: Mapped["ShipmentHeader"] = relationship("ShipmentHeader", back_populates="containers")
    container_type: Mapped["ContainerTypeLookup"] = relationship("ContainerTypeLookup")