from pydantic import BaseModel, Field, field_validator
from typing import Optional
from decimal import Decimal
from .base import BaseSchema

class LandedCostBase(BaseModel):
    shipment_header_id: int
    component_id: int  # Linked to CostComponentLookup
    service_provider_id: int  # Linked to PartnerMaster
    
    # Financials: Using Decimal for precision (Standard for Enterprise Finance)
    amount: Decimal = Field(max_digits=15, decimal_places=2, gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    invoice_reference: Optional[str] = Field(None, max_length=50)

    @field_validator('currency')
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.upper()

class LandedCostCreate(LandedCostBase):
    """Schema for creating a new cost entry."""
    pass

class LandedCostRead(LandedCostBase, BaseSchema):
    """Schema for returning cost data via API."""
    id: int
    
    # We include the name for UI display without needing extra API calls
    # These will be populated via SQLAlchemy joinedload
    component_name: Optional[str] = None
    provider_name: Optional[str] = None