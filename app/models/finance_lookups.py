from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class CostComponentLookup(Base):
    """
    Lookup for types of landed costs.
    Examples: 'FREIGHT', 'DUTY', 'INSURANCE', 'HANDLING', 'STORAGE'.
    """
    __tablename__ = "cost_component_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    component_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Flag to indicate if this is a tax/levy
    is_tax: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class CurrencyLookup(Base):
    """
    Lookup for currencies.
    Examples: 'USD', 'EUR', 'GBP'.
    """
    __tablename__ = "currency_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    currency_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    currency_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
