from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.masteraddr import MasterAddr
from app.models.partner_role import PartnerRole

if TYPE_CHECKING:
    from app.models.forwarder import Forwarder
    from app.models.supplier import Supplier
    from app.models.customer_forwarder import CustomerForwarder
    from app.models.forwarder_port import ForwarderPortMap
    from app.models.product_master import (
        MaterialCustomerMap,
        MaterialPlantData,
        MaterialSupplierMap,
    )

class PartnerMaster(Base):
    """
    Represents external entities. 
    partner_role uses strings (e.g., 'SUPPLIER', 'CARRIER') for maximum flexibility.
    """
    __tablename__ = "partner_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Modernized ID (e.g., 'VEN-100234')
    partner_identifier: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    
    # Reverted to String for flexibility
    role_id: Mapped[int] = mapped_column(ForeignKey("partner_role_lookup.id"), nullable=False)
    
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Tax/Identity
    tax_registration_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    payment_terms_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    role: Mapped["PartnerRole"] = relationship("PartnerRole")

    # Normalized Address Link
    addr_id: Mapped[int | None] = mapped_column(ForeignKey("masteraddr.id"), nullable=True)
    address: Mapped["MasterAddr"] = relationship("MasterAddr")

    forwarder_links: Mapped[list["Forwarder"]] = relationship(
        "Forwarder",
        foreign_keys="Forwarder.forwarder_id",
        back_populates="forwarder",
    )
    branch_links: Mapped[list["Forwarder"]] = relationship(
        "Forwarder",
        foreign_keys="Forwarder.branch_id",
        back_populates="branch",
    )

    supplier_links: Mapped[list["Supplier"]] = relationship(
        "Supplier",
        foreign_keys="Supplier.supplier_id",
        back_populates="supplier",
    )
    supplier_branch_links: Mapped[list["Supplier"]] = relationship(
        "Supplier",
        foreign_keys="Supplier.branch_id",
        back_populates="branch",
    )

    customer_links: Mapped[list["CustomerForwarder"]] = relationship(
        "CustomerForwarder",
        back_populates="forwarder",
    )

    forwarder_port_links: Mapped[list["ForwarderPortMap"]] = relationship(
        "ForwarderPortMap",
        back_populates="forwarder",
    )


    customer_hq_links: Mapped[list["CustomerBranch"]] = relationship(
        "CustomerBranch",
        foreign_keys="CustomerBranch.customer_id",
        back_populates="customer",
    )
    customer_branch_links: Mapped[list["CustomerBranch"]] = relationship(
        "CustomerBranch",
        foreign_keys="CustomerBranch.branch_id",
        back_populates="branch",
    )

    material_plant_data: Mapped[list["MaterialPlantData"]] = relationship(
        "MaterialPlantData",
        foreign_keys="MaterialPlantData.branch_id",
        back_populates="branch",
    )
    material_supplier_maps: Mapped[list["MaterialSupplierMap"]] = relationship(
        "MaterialSupplierMap",
        foreign_keys="MaterialSupplierMap.supplier_id",
        back_populates="supplier",
    )
    material_customer_maps: Mapped[list["MaterialCustomerMap"]] = relationship(
        "MaterialCustomerMap",
        foreign_keys="MaterialCustomerMap.customer_id",
        back_populates="customer",
    )

    # Metadata
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Partner(id='{self.partner_identifier}', role='{self.partner_role}')>"
