from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ProductTypeLookup(Base):
    """Lookup for categories like 'GOODS', 'SERVICE', 'SOFTWARE'."""
    __tablename__ = "product_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class UomLookup(Base):
    """Lookup for units like 'EA', 'KG', 'PAL', etc."""
    __tablename__ = "uom_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uom_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    uom_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Useful for logistics logic (e.g., only calculate weight for MASS types)
    uom_class: Mapped[str | None] = mapped_column(String(20), nullable=True) 
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)