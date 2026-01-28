from sqlalchemy import String, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class MasterAddr(AuditMixin, Base):
    __tablename__ = "masteraddr"
    __table_args__ = ( UniqueConstraint("name", "type", name="uq_masteraddr_name_type"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # "type" is fine as a column name, but in Python we name the attribute addr_type
    addr_type: Mapped[str | None] = mapped_column("type", String(50), nullable=False)

    country: Mapped[str | None] = mapped_column(String(2), nullable=True)   # e.g. "ES"
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(20), nullable=True)

    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    housenumber: Mapped[str | None] = mapped_column(String(20), nullable=True)

    phone1: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone2: Mapped[str | None] = mapped_column(String(30), nullable=True)
    emailid: Mapped[str | None] = mapped_column(String(255), nullable=True)

    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "Europe/Madrid"

    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)

    deletion_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
