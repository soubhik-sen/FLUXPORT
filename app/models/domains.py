from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Domain(Base):
    __tablename__ = "domains"

    __table_args__ = (
        # one technical key per domain (e.g., ORDER_STATUS + SHP)
        UniqueConstraint("domain_name", "technical_key", name="uq_domains_name_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    domain_name: Mapped[str] = mapped_column(String(80), nullable=False)
    technical_key: Mapped[str] = mapped_column(String(40), nullable=False)

    display_label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
