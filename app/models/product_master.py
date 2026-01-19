from sqlalchemy import String, Boolean, Float, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.product_lookups import ProductTypeLookup, UomLookup

class ProductMaster(Base):
    __tablename__ = "product_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_identifier: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    
    # FKs to Lookup Tables
    type_id: Mapped[int] = mapped_column(ForeignKey("product_type_lookup.id"), nullable=False)
    uom_id: Mapped[int] = mapped_column(ForeignKey("uom_lookup.id"), nullable=False)
    
    short_description: Mapped[str] = mapped_column(String(255), nullable=False)
    detailed_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    hs_code: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(2), nullable=True)
    
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships for easy access
    product_type: Mapped["ProductTypeLookup"] = relationship("ProductTypeLookup")
    uom: Mapped["UomLookup"] = relationship("UomLookup")

    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Product(sku='{self.sku_identifier}')>"