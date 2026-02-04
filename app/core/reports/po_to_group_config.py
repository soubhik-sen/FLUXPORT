from sqlalchemy.orm import aliased

from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.models.po_schedule_line import POScheduleLine
from app.models.shipment import ShipmentHeader, ShipmentItem, ShipmentContainer
from app.models.product_master import ProductMaster
from app.models.partner_master import PartnerMaster
from app.models.logistics_lookups import ShipmentStatusLookup, TransportModeLookup
from app.models.product_lookups import ProductTypeLookup, UomLookup

# --- ENTERPRISE ALIASES ---
# Essential for resolving AmbiguousForeignKeysError when joining PartnerMaster twice
VendorPartner = aliased(PartnerMaster, name="vendor_partner")
CarrierPartner = aliased(PartnerMaster, name="carrier_partner")
ShipmentHeaderJoin = (ShipmentHeader, POScheduleLine.shipment_header_id == ShipmentHeader.id)
ShipmentItemJoin = (ShipmentItem, ShipmentItem.po_schedule_line_id == POScheduleLine.id)
ShipmentContainerJoin = (ShipmentContainer, ShipmentContainer.shipment_header_id == ShipmentHeader.id)
ShipmentStatusJoin = (ShipmentStatusLookup, ShipmentHeader.status_id == ShipmentStatusLookup.id)

PO_TO_GROUP_REPORT_CONFIG = {
    "report_id": "po_to_group",
    "base_model": PurchaseOrderHeader,
    "fields": {
        # --- GROUP: PROCUREMENT ---
        "po_no": {
            "path": PurchaseOrderHeader.po_number,
            "label": "PO Number",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "search",
            "sortable": True
        },
        "po_date": {
            "path": PurchaseOrderHeader.created_at,
            "label": "Order Date",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "date_range",
            "sortable": True
        },
        "vendor_name": {
            "path": VendorPartner.legal_name,
            "label": "Vendor",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "select",
            "join_path": [(VendorPartner, PurchaseOrderHeader.vendor_id == VendorPartner.id)]
        },
        "curr": {
            "path": VendorPartner.preferred_currency,
            "label": "Currency",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "select",
            "join_path": [(VendorPartner, PurchaseOrderHeader.vendor_id == VendorPartner.id)]
        },

        # --- GROUP: PRODUCT MASTER ---
        "sku": {
            "path": ProductMaster.sku_identifier,
            "label": "SKU",
            "group": "Product",
            "is_filterable": True,
            "filter_type": "search",
            "join_path": [PurchaseOrderItem, ProductMaster]
        },
        "prod_desc": {
            "path": ProductMaster.short_description,
            "label": "Description",
            "group": "Product",
            "is_filterable": False,
            "join_path": [PurchaseOrderItem, ProductMaster]
        },
        "prod_type": {
            "path": ProductTypeLookup.type_name,
            "label": "Type",
            "group": "Product",
            "is_filterable": True,
            "filter_type": "select",
            "join_path": [PurchaseOrderItem, ProductMaster, ProductTypeLookup]
        },
        "uom": {
            "path": UomLookup.uom_code,
            "label": "UOM",
            "group": "Product",
            "is_filterable": True,
            "filter_type": "select",
            "join_path": [PurchaseOrderItem, ProductMaster, UomLookup]
        },

        # --- GROUP: LINE ITEMS & PLANNING ---
        "item_price": {
            "path": PurchaseOrderItem.unit_price,
            "label": "Unit Price",
            "group": "Commercial",
            "is_filterable": True,
            "filter_type": "numeric_range",
            "join_path": [PurchaseOrderItem]
        },
        "ord_qty": {
            "path": PurchaseOrderItem.quantity,
            "label": "Ordered Qty",
            "group": "Commercial",
            "is_filterable": True,
            "filter_type": "numeric_range",
            "join_path": [PurchaseOrderItem]
        },
        "sch_qty": {
            "path": POScheduleLine.quantity,
            "label": "Scheduled Qty",
            "group": "Planning",
            "is_filterable": True,
            "filter_type": "numeric_range",
            "join_path": [PurchaseOrderItem, POScheduleLine]
        },
        "prom_date": {
            "path": POScheduleLine.delivery_date,
            "label": "Promised Date",
            "group": "Planning",
            "is_filterable": True,
            "filter_type": "date_range",
            "join_path": [PurchaseOrderItem, POScheduleLine]
        },

        # --- GROUP: LOGISTICS ---
        "ship_no": {
            "path": ShipmentHeader.shipment_number,
            "label": "Shipment #",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "search",
            "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeaderJoin]
        },
        "carrier_id": {
            "path": CarrierPartner.partner_identifier,
            "label": "Carrier ID",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "select",
            "join_path": [
                PurchaseOrderItem,
                POScheduleLine,
                ShipmentHeaderJoin,
                (CarrierPartner, ShipmentHeader.carrier_id == CarrierPartner.id)
            ]
        },
        "ship_status": {
            "path": ShipmentStatusLookup.status_name,
            "label": "Status",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "select",
            "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeaderJoin, ShipmentStatusJoin],
            "formatter": "status_icon",
            "icon_rules": [
                {"value": "DRAFT", "icon": "inventory_2", "color": "grey"},
                {"value": "BOOKED", "icon": "confirmation_number", "color": "blue"},
                {"value": "IN-TRANSIT", "icon": "local_shipping", "color": "orange"},
                {"value": "DELIVERED", "icon": "task_alt", "color": "green"},
                {"value": "CANCELLED", "icon": "cancel", "color": "red"}
            ]
        },
        "m_bol": {
            "path": ShipmentHeader.master_bill_lading,
            "label": "M-BOL",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "search",
            "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeaderJoin]
        },
        "eta": {
            "path": ShipmentHeader.estimated_arrival,
            "label": "ETA",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "date_range",
            "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeaderJoin]
        },
        "shipped_qty": {
            "path": ShipmentItem.shipped_qty,
            "label": "Shipped Qty",
            "group": "Packing",
            "is_filterable": True,
            "filter_type": "numeric_range",
            "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentItemJoin]
        },
        "cont_no": {
            "path": ShipmentContainer.container_number,
            "label": "Container #",
            "group": "Packing",
            "is_filterable": True,
            "filter_type": "search",
            "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeaderJoin, ShipmentContainerJoin]
        },
    },
    "default_columns": ["po_no", "vendor_name", "sku", "sch_qty", "prom_date", "ship_status", "eta"]
}
