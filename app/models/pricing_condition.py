from sqlalchemy import String, Float, ForeignKey, DateTime, func, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.pricing_type import PricingType # Import the lookup

class PricingCondition(Base):
    """
    Stores pricing rules for Products or specific Partners.
    Now references pricing_type_lookup for categories.
    """
    __tablename__ = "pricing_condition"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    product_id: Mapped[int] = mapped_column(ForeignKey("product_master.id"), nullable=False)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partner_master.id"), nullable=True)
    
    # FK to lookup instead of Enum
    type_id: Mapped[int] = mapped_column(ForeignKey("pricing_type_lookup.id"), nullable=False)
    
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    
    valid_from: Mapped[object] = mapped_column(Date, nullable=False)
    valid_to: Mapped[object] = mapped_column(Date, nullable=False)

    # Relationships
    pricing_type: Mapped["PricingType"] = relationship("PricingType")
    
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())