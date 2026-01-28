from fastapi import APIRouter
from app.api.v1.endpoints import purchase_orders, shipments, customers, partners
from app.api.v1.endpoints.lookup_factory import create_lookup_router
# --- MODEL IMPORTS (From your discovery list) ---
from app.models.product_lookups import UomLookup
from app.models.po_lookups import (
    PurchaseOrderStatusLookup, 
    PurchaseOrderTypeLookup, 
    PurchaseOrgLookup,
    PurchaseOrderItemStatusLookup
)
from app.models.logistics_lookups import (
    ShipmentStatusLookup,
    TransportModeLookup,
    MilestoneTypeLookup,
    ContainerTypeLookup
)
from app.models.finance_lookups import CostComponentLookup, CurrencyLookup
from app.models.doc_lookups import DocumentTypeLookup
from app.models.text_lookups import TextTypeLookup
from app.models.customer_role import CustomerRole
from app.models.partner_role import PartnerRole

# --- SCHEMA IMPORTS ---
# Note: Assuming you follow the naming convention ModelName + "Schema"
from app.schemas.lookups import (
    UomLookupSchema, PurchaseOrderStatusLookupSchema, PurchaseOrderTypeLookupSchema,
    PurchaseOrgLookupSchema, PurchaseOrderItemStatusLookupSchema,
    ShipmentStatusLookupSchema, TransportModeLookupSchema, MilestoneTypeLookupSchema,
    ContainerTypeLookupSchema, CostComponentLookupSchema, CurrencyLookupSchema, DocumentTypeLookupSchema,
    TextTypeLookupSchema, CustomerRoleLookupSchema, PartnerRoleLookupSchema
)

api_router = APIRouter()

# Registering specialized controllers
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["Commercial"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["Logistics"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(partners.router, prefix="/partners", tags=["Partners"])

# ENTERPRISE LOOKUP TABLE: Map your models to their configurations
LOOKUP_CONFIG = [
    # --- PRODUCT ---
    {"model": UomLookup, "schema": UomLookupSchema, "prefix": "/uom_lookup", "tags": ["Lookups | Product"]},

    # --- PURCHASE ORDER ---
    {"model": PurchaseOrderStatusLookup, "schema": PurchaseOrderStatusLookupSchema, "prefix": "/po_status_lookup", "tags": ["Lookups | PO"]},
    {"model": PurchaseOrderTypeLookup, "schema": PurchaseOrderTypeLookupSchema, "prefix": "/po_type_lookup", "tags": ["Lookups | PO"]},
    {"model": PurchaseOrgLookup, "schema": PurchaseOrgLookupSchema, "prefix": "/purchase_org_lookup", "tags": ["Lookups | PO"]},
    {"model": PurchaseOrderItemStatusLookup, "schema": PurchaseOrderItemStatusLookupSchema, "prefix": "/po_item_status_lookup", "tags": ["Lookups | PO"]},

    # --- LOGISTICS ---
    {"model": ShipmentStatusLookup, "schema": ShipmentStatusLookupSchema, "prefix": "/shipment_status_lookup", "tags": ["Lookups | Logistics"]},
    {"model": TransportModeLookup, "schema": TransportModeLookupSchema, "prefix": "/transport_mode_lookup", "tags": ["Lookups | Logistics"]},
    {"model": MilestoneTypeLookup, "schema": MilestoneTypeLookupSchema, "prefix": "/milestone_type_lookup", "tags": ["Lookups | Logistics"]},
    {"model": ContainerTypeLookup, "schema": ContainerTypeLookupSchema, "prefix": "/container_type_lookup", "tags": ["Lookups | Logistics"]},

    # --- FINANCE ---
    {"model": CostComponentLookup, "schema": CostComponentLookupSchema, "prefix": "/cost_component_lookup", "tags": ["Lookups | Finance"]},
    {"model": CurrencyLookup, "schema": CurrencyLookupSchema, "prefix": "/currency_lookup", "tags": ["Lookups | Finance"]},

    # --- SYSTEM / METADATA ---
    {"model": PartnerRole, "schema": PartnerRoleLookupSchema, "prefix": "/partner_role_lookup", "tags": ["Lookups | System"]},
    {"model": CustomerRole, "schema": CustomerRoleLookupSchema, "prefix": "/customer_role_lookup", "tags": ["Lookups | System"]},
    {"model": DocumentTypeLookup, "schema": DocumentTypeLookupSchema, "prefix": "/document_type_lookup", "tags": ["Lookups | System"]},
    {"model": TextTypeLookup, "schema": TextTypeLookupSchema, "prefix": "/text_type_lookup", "tags": ["Lookups | System"]},
]

# Automatically mount all lookup routers
for cfg in LOOKUP_CONFIG:
    router = create_lookup_router(
        model=cfg["model"],
        schema=cfg["schema"],
        name=cfg["prefix"],
        tags=cfg["tags"]
    )
    api_router.include_router(router, prefix=cfg["prefix"])
