from sqlalchemy import Date, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.masteraddr import MasterAddr
from app.models.partner_master import PartnerMaster


class Supplier(Base):
    __tablename__ = "supplier"

    __table_args__ = (
        UniqueConstraint("supplier_id", "branch_id", "valid_from", name="uq_supplier_map"),
        CheckConstraint("supplier_id <> branch_id", name="ck_supplier_not_same_as_branch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    supplier: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        foreign_keys=[supplier_id],
        back_populates="supplier_links",
    )
    branch: Mapped["PartnerMaster"] = relationship(
        "PartnerMaster",
        foreign_keys=[branch_id],
        back_populates="supplier_branch_links",
    )

    # Normalized Address Link
    addr_id: Mapped[int | None] = mapped_column(ForeignKey("masteraddr.id"), nullable=True)
    address: Mapped["MasterAddr"] = relationship("MasterAddr")

    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
