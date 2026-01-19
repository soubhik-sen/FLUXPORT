from sqlalchemy import String, ForeignKey, DateTime, func, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.finance_lookups import CostComponentLookup
from app.models.partner_master import PartnerMaster
from app.models.shipment import ShipmentHeader

class LandedCostEntry(Base):
    """
    Records actual expenses related to shipments.
    Used for final product margin and landed cost analysis.
    """
    __tablename__ = "landed_cost_entry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Reference to the Shipment
    shipment_header_id: Mapped[int] = mapped_column(ForeignKey("shipment_header.id"), nullable=False)
    
    # FK to Cost Component Lookup
    component_id: Mapped[int] = mapped_column(ForeignKey("cost_component_lookup.id"), nullable=False)
    
    # Which Service Provider is charging this? (e.g., Forwarder, Customs)
    service_provider_id: Mapped[int] = mapped_column(ForeignKey("partner_master.id"), nullable=False)
    
    # Financial details
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    
    # Reference for the invoice provided by the agent
    invoice_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    shipment: Mapped["ShipmentHeader"] = relationship("ShipmentHeader")
    component: Mapped["CostComponentLookup"] = relationship("CostComponentLookup")
    provider: Mapped["PartnerMaster"] = relationship("PartnerMaster")

    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())