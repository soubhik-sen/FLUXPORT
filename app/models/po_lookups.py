from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class PurchaseOrderStatusLookup(Base):
    """Lookup for PO lifecycle statuses (e.g., DRAFT, APPROVED)."""
    __tablename__ = "po_status_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

class PurchaseOrderTypeLookup(Base):
    """
    Lookup for PO Document Types. 
    Examples: 'STND' (Standard), 'SERV' (Service), 'STRN' (Stock Transfer).
    """
    __tablename__ = "po_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

# ... (existing PurchaseOrderStatusLookup and PurchaseOrderTypeLookup)

class PurchaseOrgLookup(Base):
    """
    Lookup for Purchase Organizations.
    Examples: 'DOM-PROC' (Domestic Procurement), 'INTL-EXP' (International Export).
    """
    __tablename__ = "purchase_org_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    org_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

class PurchaseOrderItemStatusLookup(Base):
    """
    Lookup for individual PO line item statuses.
    Examples: 'OPEN', 'SHIPPED', 'RECEIVED', 'CANCELLED'.
    """
    __tablename__ = "po_item_status_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class IncotermLookup(Base):
    """
    Lookup for Incoterms (e.g., EXW, FOB, CIF).
    """
    __tablename__ = "incoterm_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incoterm: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    incoterm_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
