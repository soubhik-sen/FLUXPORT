from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.base import Base
from app.models.mixins import AuditMixin
from app.models.product_lookups import ProductTypeLookup, UomLookup

if TYPE_CHECKING:
    from app.models.partner_master import PartnerMaster


class ProductMaster(AuditMixin, Base):
    __tablename__ = "material_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)

    material_type_id: Mapped[int] = mapped_column(
        ForeignKey("product_type_lookup.id", ondelete="RESTRICT"),
        nullable=False,
    )
    base_uom_id: Mapped[int] = mapped_column(
        ForeignKey("uom_lookup.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Material attributes
    hs_code: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)

    # Legacy compatibility fields (retained for existing reports/UI)
    short_description: Mapped[str] = mapped_column(String(255), nullable=False)
    detailed_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(2), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    volume_m3: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    material_type: Mapped["ProductTypeLookup"] = relationship(
        "ProductTypeLookup",
        back_populates="materials_by_type",
    )
    base_uom: Mapped["UomLookup"] = relationship(
        "UomLookup",
        foreign_keys=[base_uom_id],
        back_populates="materials_as_base_uom",
    )

    texts: Mapped[list["MaterialText"]] = relationship(
        "MaterialText",
        back_populates="material",
    )
    plant_data: Mapped[list["MaterialPlantData"]] = relationship(
        "MaterialPlantData",
        back_populates="material",
    )
    uom_conversions: Mapped[list["MaterialUomConversion"]] = relationship(
        "MaterialUomConversion",
        back_populates="material",
    )
    supplier_maps: Mapped[list["MaterialSupplierMap"]] = relationship(
        "MaterialSupplierMap",
        back_populates="material",
    )
    customer_maps: Mapped[list["MaterialCustomerMap"]] = relationship(
        "MaterialCustomerMap",
        back_populates="material",
    )

    # Backwards-compatible attribute aliases
    sku_identifier = synonym("part_number")
    type_id = synonym("material_type_id")
    uom_id = synonym("base_uom_id")

    def __repr__(self) -> str:
        return f"<Material(part_number='{self.part_number}')>"


class MaterialText(AuditMixin, Base):
    """
    Internationalized material descriptions (EN/PT/ES).
    """

    __tablename__ = "material_text"
    __table_args__ = (
        # Enforce one text per language per material
        UniqueConstraint("material_id", "language_code", name="uq_material_text_material_language"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("material_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    language_code: Mapped[str] = mapped_column(String(2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    long_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    material: Mapped["ProductMaster"] = relationship(
        "ProductMaster",
        back_populates="texts",
    )


class MaterialPlantData(AuditMixin, Base):
    """
    Plant / Branch-specific material settings.
    """

    __tablename__ = "material_plant_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("material_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_purchasable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    safety_stock_qty: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    default_lead_time: Mapped[int | None] = mapped_column(Integer, nullable=True)

    material: Mapped["ProductMaster"] = relationship(
        "ProductMaster",
        back_populates="plant_data",
    )
    branch: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        foreign_keys=[branch_id],
        back_populates="material_plant_data",
    )


class MaterialUomConversion(AuditMixin, Base):
    """
    Alternative UOM * (Numerator / Denominator) = Base UOM.
    """

    __tablename__ = "material_uom_conversion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("material_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    alternative_uom_id: Mapped[int] = mapped_column(
        ForeignKey("uom_lookup.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numerator: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    denominator: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)

    material: Mapped["ProductMaster"] = relationship(
        "ProductMaster",
        back_populates="uom_conversions",
    )
    alternative_uom: Mapped["UomLookup"] = relationship(
        "UomLookup",
        foreign_keys=[alternative_uom_id],
        back_populates="material_uom_conversions",
    )


class MaterialSupplierMap(AuditMixin, Base):
    """
    Supplier info record for a material.
    """

    __tablename__ = "material_supplier_map"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("material_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_part_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_order_qty: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)

    material: Mapped["ProductMaster"] = relationship(
        "ProductMaster",
        back_populates="supplier_maps",
    )
    supplier: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        foreign_keys=[supplier_id],
        back_populates="material_supplier_maps",
    )


class MaterialCustomerMap(AuditMixin, Base):
    """
    Customer info record for a material.
    """

    __tablename__ = "material_customer_map"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("material_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_part_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sales_uom_id: Mapped[int] = mapped_column(
        ForeignKey("uom_lookup.id", ondelete="RESTRICT"),
        nullable=False,
    )

    material: Mapped["ProductMaster"] = relationship(
        "ProductMaster",
        back_populates="customer_maps",
    )
    customer: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        foreign_keys=[customer_id],
        back_populates="material_customer_maps",
    )
    sales_uom: Mapped["UomLookup"] = relationship(
        "UomLookup",
        foreign_keys=[sales_uom_id],
        back_populates="material_customer_sales_uoms",
    )


# Domain-friendly alias
MaterialMaster = ProductMaster
