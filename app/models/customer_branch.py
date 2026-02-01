
from sqlalchemy import Date, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.partner_master import PartnerMaster


class CustomerBranch(Base):
    __tablename__ = "customer"

    __table_args__ = (
        UniqueConstraint("customer_id", "branch_id", "valid_from", name="uq_customer_map"),
        CheckConstraint("customer_id <> branch_id", name="ck_customer_not_same_as_branch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    customer: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        foreign_keys=[customer_id],
        back_populates="customer_hq_links",
    )
    branch: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        foreign_keys=[branch_id],
        back_populates="customer_branch_links",
    )

    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
