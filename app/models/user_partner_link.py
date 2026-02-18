from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import AuditMixin


class UserPartnerLink(AuditMixin, Base):
    __tablename__ = "user_partner_map"

    __table_args__ = (
        UniqueConstraint("user_email", "partner_id", name="uq_user_partner"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.email", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user = relationship("User")
    partner = relationship("PartnerMaster")

    @property
    def user_name(self) -> str | None:
        if not self.user:
            return None
        return self.user.username or self.user.email

    @property
    def partner_name(self) -> str | None:
        if not self.partner:
            return None
        return (
            self.partner.trade_name
            or self.partner.legal_name
            or self.partner.partner_identifier
        )

    @property
    def partner_code(self) -> str | None:
        if not self.partner:
            return None
        return self.partner.partner_identifier
