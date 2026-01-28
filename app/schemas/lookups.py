from pydantic import Field
from typing import Optional
from .base import LookupBase

# --- PRODUCT LOOKUPS ---
class UomLookupSchema(LookupBase):
    code: str = Field(validation_alias="uom_code", serialization_alias="code")
    name: str = Field(validation_alias="uom_name", serialization_alias="name")

# --- PROCUREMENT LOOKUPS ---
class PurchaseOrderStatusLookupSchema(LookupBase):
    code: str = Field(validation_alias="status_code", serialization_alias="code")
    name: str = Field(validation_alias="status_name", serialization_alias="name")

class PurchaseOrderTypeLookupSchema(LookupBase):
    code: str = Field(validation_alias="type_code", serialization_alias="code")
    name: str = Field(validation_alias="type_name", serialization_alias="name")

class PurchaseOrgLookupSchema(LookupBase):
    code: str = Field(validation_alias="org_code", serialization_alias="code")
    name: str = Field(validation_alias="org_name", serialization_alias="name")

class PurchaseOrderItemStatusLookupSchema(LookupBase):
    code: str = Field(validation_alias="item_status_code", serialization_alias="code")
    name: str = Field(validation_alias="item_status_name", serialization_alias="name")

# --- LOGISTICS LOOKUPS ---
class ShipmentStatusLookupSchema(LookupBase):
    code: str = Field(validation_alias="shipment_status_code", serialization_alias="code")
    name: str = Field(validation_alias="shipment_status_name", serialization_alias="name")

class TransportModeLookupSchema(LookupBase):
    code: str = Field(validation_alias="mode_code", serialization_alias="code")
    name: str = Field(validation_alias="mode_name", serialization_alias="name")

class MilestoneTypeLookupSchema(LookupBase):
    code: str = Field(validation_alias="milestone_code", serialization_alias="code")
    name: str = Field(validation_alias="milestone_name", serialization_alias="name")

class ContainerTypeLookupSchema(LookupBase):
    code: str = Field(validation_alias="container_code", serialization_alias="code")
    name: str = Field(validation_alias="container_name", serialization_alias="name")

# --- FINANCE, DOC, AND TEXT ---
class CostComponentLookupSchema(LookupBase):
    code: str = Field(validation_alias="cost_code", serialization_alias="code")
    name: str = Field(validation_alias="cost_name", serialization_alias="name")

class CurrencyLookupSchema(LookupBase):
    code: str = Field(validation_alias="currency_code", serialization_alias="code")
    name: str = Field(validation_alias="currency_name", serialization_alias="name")

class DocumentTypeLookupSchema(LookupBase):
    code: str = Field(validation_alias="doc_code", serialization_alias="code")
    name: str = Field(validation_alias="doc_name", serialization_alias="name")

class TextTypeLookupSchema(LookupBase):
    code: str = Field(validation_alias="text_code", serialization_alias="code")
    name: str = Field(validation_alias="text_name", serialization_alias="name")

# --- PARTNER ---
class PartnerRoleLookupSchema(LookupBase):
    code: str = Field(validation_alias="role_code", serialization_alias="code")
    name: str = Field(validation_alias="role_name", serialization_alias="name")

# --- CUSTOMER ---
class CustomerRoleLookupSchema(LookupBase):
    code: str = Field(validation_alias="role_code", serialization_alias="code")
    name: str = Field(validation_alias="role_name", serialization_alias="name")
