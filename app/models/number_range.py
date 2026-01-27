from sqlalchemy import String, Integer, BigInteger, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

class Base(DeclarativeBase):
    pass

class SysNumberRange(Base):
    __tablename__ = "sys_number_ranges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # High-level category: 'PO', 'INV', 'GRN'
    doc_category: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Specific type: References your po_type_lookup.id (or inv_type_lookup.id)
    # We use a generic integer here to keep the table reusable across modules
    doc_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., 'PUR-'
    current_value: Mapped[int] = mapped_column(BigInteger, default=0)
    padding: Mapped[int] = mapped_column(Integer, default=5)         # e.g., 5 -> 00001
    
    # Feature toggles for formatting
    include_year: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Reusability Guard: Ensure one sequence per category/type pair
    __table_args__ = (
        UniqueConstraint('doc_category', 'doc_type_id', name='uix_category_type'),
    )