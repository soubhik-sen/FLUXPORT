from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import AuditMixin

class ProductTypeLookup(AuditMixin, Base):
    """Lookup for categories like 'GOODS', 'SERVICE', 'SOFTWARE'."""
    __tablename__ = "product_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    materials_by_type: Mapped[list["ProductMaster"]] = relationship(
        "ProductMaster",
        back_populates="material_type",
    )

class UomLookup(AuditMixin, Base):
    """Lookup for units like 'EA', 'KG', 'PAL', etc."""
    __tablename__ = "uom_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uom_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    uom_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Useful for logistics logic (e.g., only calculate weight for MASS types)
    uom_class: Mapped[str | None] = mapped_column(String(20), nullable=True) 
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    materials_as_base_uom: Mapped[list["ProductMaster"]] = relationship(
        "ProductMaster",
        back_populates="base_uom",
        foreign_keys="ProductMaster.base_uom_id",
    )
    material_uom_conversions: Mapped[list["MaterialUomConversion"]] = relationship(
        "MaterialUomConversion",
        back_populates="alternative_uom",
        foreign_keys="MaterialUomConversion.alternative_uom_id",
    )
    material_customer_sales_uoms: Mapped[list["MaterialCustomerMap"]] = relationship(
        "MaterialCustomerMap",
        back_populates="sales_uom",
        foreign_keys="MaterialCustomerMap.sales_uom_id",
    )


if TYPE_CHECKING:
    from app.models.product_master import (
        MaterialCustomerMap,
        ProductMaster,
        MaterialUomConversion,
    )
