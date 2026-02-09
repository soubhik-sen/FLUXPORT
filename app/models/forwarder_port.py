from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.models.partner_master import PartnerMaster
    from app.models.logistics_lookups import PortLookup


class ForwarderPortMap(AuditMixin, Base):
    __tablename__ = "forwarder_port_map"

    __table_args__ = (
        UniqueConstraint("forwarder_id", "port_id", name="uq_forwarder_port"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    forwarder_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    port_id: Mapped[int] = mapped_column(
        ForeignKey("port_lookup.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    forwarder: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        back_populates="forwarder_port_links",
    )
    port: Mapped["PortLookup"] = relationship(
        "PortLookup",
        back_populates="forwarder_links",
    )

    @property
    def forwarder_name(self) -> str | None:
        if not self.forwarder:
            return None
        return (
            self.forwarder.trade_name
            or self.forwarder.legal_name
            or self.forwarder.partner_identifier
        )

    @property
    def port_label(self) -> str | None:
        if not self.port:
            return None
        return f"{self.port.port_code} - {self.port.port_name} ({self.port.country})"
