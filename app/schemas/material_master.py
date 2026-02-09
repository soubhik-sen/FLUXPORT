from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MaterialMasterBase(BaseModel):
    part_number: str = Field(min_length=1, max_length=40)
    material_type_id: int = Field(ge=1)
    base_uom_id: int = Field(ge=1)
    hs_code: str | None = Field(default=None, max_length=15)
    short_description: str = Field(min_length=1, max_length=255)
    detailed_description: str | None = Field(default=None, max_length=1000)
    country_of_origin: str | None = Field(default=None, min_length=2, max_length=2)
    weight_kg: Decimal | None = None
    volume_m3: Decimal | None = None
    is_active: bool = True
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialMasterCreate(MaterialMasterBase):
    pass


class MaterialMasterUpdate(BaseModel):
    part_number: str | None = Field(default=None, min_length=1, max_length=40)
    material_type_id: int | None = Field(default=None, ge=1)
    base_uom_id: int | None = Field(default=None, ge=1)
    hs_code: str | None = Field(default=None, max_length=15)
    short_description: str | None = Field(default=None, min_length=1, max_length=255)
    detailed_description: str | None = Field(default=None, max_length=1000)
    country_of_origin: str | None = Field(default=None, min_length=2, max_length=2)
    weight_kg: Decimal | None = None
    volume_m3: Decimal | None = None
    is_active: bool | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialMasterOut(MaterialMasterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MaterialTextBase(BaseModel):
    material_id: int = Field(ge=1)
    language_code: str = Field(min_length=2, max_length=2)
    description: str | None = Field(default=None, max_length=255)
    long_text: str | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialTextCreate(MaterialTextBase):
    pass


class MaterialTextUpdate(BaseModel):
    material_id: int | None = Field(default=None, ge=1)
    language_code: str | None = Field(default=None, min_length=2, max_length=2)
    description: str | None = Field(default=None, max_length=255)
    long_text: str | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialTextOut(MaterialTextBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MaterialPlantDataBase(BaseModel):
    material_id: int = Field(ge=1)
    branch_id: int = Field(ge=1)
    is_purchasable: bool = False
    safety_stock_qty: Decimal | None = None
    default_lead_time: int | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialPlantDataCreate(MaterialPlantDataBase):
    pass


class MaterialPlantDataUpdate(BaseModel):
    material_id: int | None = Field(default=None, ge=1)
    branch_id: int | None = Field(default=None, ge=1)
    is_purchasable: bool | None = None
    safety_stock_qty: Decimal | None = None
    default_lead_time: int | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialPlantDataOut(MaterialPlantDataBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MaterialUomConversionBase(BaseModel):
    material_id: int = Field(ge=1)
    alternative_uom_id: int = Field(ge=1)
    numerator: Decimal
    denominator: Decimal
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialUomConversionCreate(MaterialUomConversionBase):
    pass


class MaterialUomConversionUpdate(BaseModel):
    material_id: int | None = Field(default=None, ge=1)
    alternative_uom_id: int | None = Field(default=None, ge=1)
    numerator: Decimal | None = None
    denominator: Decimal | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialUomConversionOut(MaterialUomConversionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MaterialSupplierMapBase(BaseModel):
    material_id: int = Field(ge=1)
    supplier_id: int = Field(ge=1)
    supplier_part_number: str | None = Field(default=None, max_length=64)
    is_preferred: bool = False
    min_order_qty: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialSupplierMapCreate(MaterialSupplierMapBase):
    pass


class MaterialSupplierMapUpdate(BaseModel):
    material_id: int | None = Field(default=None, ge=1)
    supplier_id: int | None = Field(default=None, ge=1)
    supplier_part_number: str | None = Field(default=None, max_length=64)
    is_preferred: bool | None = None
    min_order_qty: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialSupplierMapOut(MaterialSupplierMapBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MaterialCustomerMapBase(BaseModel):
    material_id: int = Field(ge=1)
    customer_id: int = Field(ge=1)
    customer_part_number: str | None = Field(default=None, max_length=64)
    sales_uom_id: int = Field(ge=1)
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialCustomerMapCreate(MaterialCustomerMapBase):
    pass


class MaterialCustomerMapUpdate(BaseModel):
    material_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_part_number: str | None = Field(default=None, max_length=64)
    sales_uom_id: int | None = Field(default=None, ge=1)
    created_by: str | None = Field(default=None, max_length=255)
    last_changed_by: str | None = Field(default=None, max_length=255)


class MaterialCustomerMapOut(MaterialCustomerMapBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
