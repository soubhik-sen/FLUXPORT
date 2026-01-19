from sqlalchemy import String, Boolean, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class SystemQualifier(Base):
    """
    Generic lookup table for system-wide constants and dropdowns.
    Used for: PO Statuses, Incoterms, Shipping Modals, Document Types.
    """
    __tablename__ = "system_qualifier"
    __table_args__ = (
        UniqueConstraint("category", "code", name="uq_category_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # E.g., 'PO_STATUS', 'INCOTERM', 'SHIP_MODAL'
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # E.g., 'APPR', 'FOB', 'SEA'
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # User-friendly label: 'Approved', 'Free on Board', 'Ocean Freight'
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Audit
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())