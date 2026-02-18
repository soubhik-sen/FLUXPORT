from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import AuditMixin


class UserCustomerLink(AuditMixin, Base):
    __tablename__ = "user_customer_map"

    __table_args__ = (
        UniqueConstraint("user_email", "customer_id", name="uq_user_customer"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.email", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customer_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user = relationship("User")
    customer = relationship("CustomerMaster")

    @property
    def user_name(self) -> str | None:
        if not self.user:
            return None
        return self.user.username or self.user.email

    @property
    def customer_name(self) -> str | None:
        if not self.customer:
            return None
        return (
            self.customer.trade_name
            or self.customer.legal_name
            or self.customer.customer_identifier
        )

    @property
    def customer_code(self) -> str | None:
        if not self.customer:
            return None
        return self.customer.customer_identifier

    @property
    def company_id(self) -> int | None:
        if not self.customer:
            return None
        return self.customer.company_id

    @property
    def company_name(self) -> str | None:
        if not self.customer or not self.customer.company:
            return None
        return self.customer.company.legal_name
