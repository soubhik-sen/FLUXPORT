from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TextTypeLookup(Base):
    """
    Lookup for types of text entries.
    Examples: 'VEND_INST' (Vendor Instructions), 'INT_NOTE' (Internal Note), 
    'SHIP_MARK' (Shipping Marks), 'DECLARATION' (Customs Declaration).
    """
    __tablename__ = "text_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text_type_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    text_type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Logic flags
    is_external: Mapped[bool] = mapped_column(Boolean, default=False) # True if visible to Partners
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())