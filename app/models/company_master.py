from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.masteraddr import MasterAddr

from app.db.base import Base
# Import the MasterAddr model to allow relationship discovery
# from .master_addr import MasterAddr 

class CompanyMaster(Base):
    """
    Represents the internal legal entities and branches (Unidades).
    Links to MasterAddr for all geographic and contact information.
    """
    __tablename__ = "company_master"

    # 1. Identity & Governance
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # SAP Mapping: BUKRS (Company Code)
    company_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    
    # Differentiation for regional branches (e.g., "RIO", "SP")
    branch_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # SAP Mapping: STCEG (Tax Registration Number)
    tax_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 2. Relationship to Master Address Table
    # All city, country, phone, and timezone data is fetched via this link
    addr_id: Mapped[int | None] = mapped_column(ForeignKey("masteraddr.id"), nullable=True)
    
    # SQLAlchemy relationship for easy access (e.g., company.address.city)
    address: Mapped["MasterAddr"] = relationship("MasterAddr")

    # 3. Financial/Internal Metadata
    # Ref: SAP WAERS (Default currency for the branch)
    default_currency: Mapped[str] = mapped_column(String(5), nullable=False, default="USD")

    # 4. Audit Metadata
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<CompanyMaster(code='{self.company_code}', branch='{self.branch_code}', name='{self.trade_name}')>"