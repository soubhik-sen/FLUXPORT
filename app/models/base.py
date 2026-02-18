# Import the declarative base
from app.db.base import Base  # This is the class we created in the last step

# Import all models for Alembic/SQLAlchemy discovery
# Note: These imports are required so that they register themselves on Base.metadata
from app.models.partner_master import PartnerMaster
from app.models.customer_master import CustomerMaster
from app.models.customer_role import CustomerRole
from app.models.customer_forwarder import CustomerForwarder
from app.models.company_master import CompanyMaster
from app.models.product_master import (
    MaterialCustomerMap,
    MaterialMaster,
    MaterialPlantData,
    MaterialSupplierMap,
    MaterialText,
    MaterialUomConversion,
    ProductMaster,
)
from app.models.product_lookups import UomLookup
from app.models.po_lookups import (
    PurchaseOrderStatusLookup, 
    PurchaseOrderTypeLookup, 
    PurchaseOrgLookup,
    PurchaseOrderItemStatusLookup,
    IncotermLookup
)
from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.models.logistics_lookups import (
    ShipmentStatusLookup,
    TransportModeLookup,
    MilestoneTypeLookup,
    ContainerTypeLookup,
    PortLookup
)
from app.models.forwarder_port import ForwarderPortMap
from app.models.shipment import (
    ShipmentHeader, 
    ShipmentItem, 
    ShipmentMilestone, 
    ShipmentContainer
)
from app.models.finance_lookups import CostComponentLookup, CurrencyLookup
from app.models.landed_cost import LandedCostEntry
from app.models.doc_lookups import DocumentTypeLookup
from app.models.document import DocumentAttachment
from app.models.text_lookups import TextTypeLookup
from app.models.text_master import TextMaster
from app.models.doc_text import DocText, TextVal
from app.models.workflow_rules import SysWorkflowRule
from app.models.event_lookup import EventLookup
from app.models.decision_history import DecisionHistory
from app.models.event_profile import EventProfile, ProfileEventMap, EventInstance
from app.models.metadata_framework import (
    MetadataAuditLog,
    MetadataRegistry,
    MetadataVersion,
)
from app.models.document_edit_lock import DocumentEditLock

# This allows Alembic's env.py to simply do: "from app.models.base import Base"
# and have access to the metadata for all tables.
