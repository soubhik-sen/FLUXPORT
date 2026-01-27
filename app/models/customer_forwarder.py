from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.models.customer_master import CustomerMaster
    from app.models.partner_master import PartnerMaster


class CustomerForwarder(AuditMixin, Base):
    __tablename__ = "customer_forwarder_map"

    __table_args__ = (
        UniqueConstraint("customer_id", "forwarder_id", name="uq_customer_forwarder"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customer_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    forwarder_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    customer: Mapped["CustomerMaster"] = relationship(
        "CustomerMaster",
        back_populates="forwarder_links",
    )
    forwarder: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        back_populates="customer_links",
    )

    @property
    def customer_name(self) -> str | None:
        if not self.customer:
            return None
        return self.customer.trade_name or self.customer.legal_name or self.customer.customer_identifier

    @property
    def forwarder_name(self) -> str | None:
        if not self.forwarder:
            return None
        return self.forwarder.trade_name or self.forwarder.legal_name or self.forwarder.partner_identifier
