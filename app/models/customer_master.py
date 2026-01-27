from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.customer_role import CustomerRole
from app.models.masteraddr import MasterAddr

if TYPE_CHECKING:
    from app.models.customer_forwarder import CustomerForwarder


class CustomerMaster(Base):
    """
    Represents external customer entities.
    customer_role uses strings (e.g., 'B2B', 'B2C') for flexibility.
    """
    __tablename__ = "customer_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Modernized ID (e.g., 'CUST-100234')
    customer_identifier: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    role_id: Mapped[int] = mapped_column(ForeignKey("customer_role_lookup.id"), nullable=False)

    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Tax/Identity
    tax_registration_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    payment_terms_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    role: Mapped["CustomerRole"] = relationship("CustomerRole")

    # Normalized Address Link
    addr_id: Mapped[int | None] = mapped_column(ForeignKey("masteraddr.id"), nullable=True)
    address: Mapped["MasterAddr"] = relationship("MasterAddr")

    forwarder_links: Mapped[list["CustomerForwarder"]] = relationship(
        "CustomerForwarder",
        back_populates="customer",
    )

    # Metadata
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Customer(id='{self.customer_identifier}', role_id='{self.role_id}')>"
