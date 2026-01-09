from sqlalchemy import Date, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Forwarder(Base):
    __tablename__ = "forwarder"

    __table_args__ = (
        # prevents the exact same mapping starting on same date (keeps history possible)
        UniqueConstraint("forwarder_id", "branch_id", "valid_from", name="uq_forwarder_map"),
        # basic sanity
        CheckConstraint("forwarder_id <> branch_id", name="ck_forwarder_not_same_as_branch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # both are masteraddr.id (FKs)
    forwarder_id: Mapped[int] = mapped_column(
        ForeignKey("masteraddr.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("masteraddr.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
