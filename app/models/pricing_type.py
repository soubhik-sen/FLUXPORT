from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class PricingType(Base):
    """
    Lookup table for Pricing Condition Types.
    Examples: 'BASE' (Base Price), 'DISC' (Discount), 'TAX' (Tax).
    """
    __tablename__ = "pricing_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Helpful for logic: is it an addition (+) or a deduction (-)?
    is_deduction: Mapped[bool] = mapped_column(Boolean, default=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())