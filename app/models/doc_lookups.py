from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class DocumentTypeLookup(Base):
    """
    Lookup for types of documents.
    Examples: 'CI' (Commercial Invoice), 'BOL' (Bill of Lading), 'COO' (Certificate of Origin).
    """
    __tablename__ = "document_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Requirement flags
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())