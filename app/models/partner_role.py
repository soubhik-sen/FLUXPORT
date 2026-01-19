from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class PartnerRole(Base):
    """
    Lookup table for valid Partner Roles.
    Example: 'SUPPLIER', 'CARRIER', 'FORWARDER'.
    """
    __tablename__ = "partner_role_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())