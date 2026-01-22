from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.models.po_schedule_line import POScheduleLine
from app.models.shipment import ShipmentHeader, ShipmentItem, ShipmentContainer
from app.models.product_master import ProductMaster
from app.models.partner_master import PartnerMaster
from app.models.logistics_lookups import ShipmentStatusLookup, TransportModeLookup
from app.models.product_lookups import ProductTypeLookup, UomLookup
from app.models.partner_role import PartnerRole

VISIBILITY_REPORT_CONFIG = {
    "report_id": "procurement_end_to_end",
    "base_model": PurchaseOrderHeader,
    "fields": {
        # --- GROUP: PROCUREMENT (PO HEADER) ---
        "po_no": {"path": PurchaseOrderHeader.po_number, "label": "PO Number", "group": "Procurement", "filter_type": "search", "sortable": True},
        "po_date": {"path": PurchaseOrderHeader.created_at, "label": "Order Date", "group": "Procurement", "filter_type": "date_range", "sortable": True},
        "vendor_id": {"path": PartnerMaster.partner_identifier, "label": "Vendor ID", "group": "Procurement", "join_path": [PartnerMaster]},
        "vendor_name": {"path": PartnerMaster.legal_name, "label": "Vendor Legal Name", "group": "Procurement", "join_path": [PartnerMaster]},
        "vendor_tax_id": {"path": PartnerMaster.tax_registration_id, "label": "Vendor Tax ID", "group": "Procurement", "join_path": [PartnerMaster]},
        "pay_terms": {"path": PartnerMaster.payment_terms_code, "label": "Payment Terms", "group": "Procurement", "join_path": [PartnerMaster]},
        "curr": {"path": PartnerMaster.preferred_currency, "label": "Currency", "group": "Procurement", "join_path": [PartnerMaster]},

        # --- GROUP: PRODUCT MASTER ---
        "sku": {"path": ProductMaster.sku_identifier, "label": "SKU", "group": "Product", "join_path": [PurchaseOrderItem, ProductMaster]},
        "prod_desc": {"path": ProductMaster.short_description, "label": "Product Description", "group": "Product", "join_path": [PurchaseOrderItem, ProductMaster]},
        "prod_type": {"path": ProductTypeLookup.type_name, "label": "Product Type", "group": "Product", "join_path": [PurchaseOrderItem, ProductMaster, ProductTypeLookup]},
        "uom": {"path": UomLookup.uom_code, "label": "UOM", "group": "Product", "join_path": [PurchaseOrderItem, ProductMaster, UomLookup]},
        "hs_code": {"path": ProductMaster.hs_code, "label": "HS Code", "group": "Product", "join_path": [PurchaseOrderItem, ProductMaster]},
        "coo": {"path": ProductMaster.country_of_origin, "label": "COO", "group": "Product", "join_path": [PurchaseOrderItem, ProductMaster]},

        # --- GROUP: LINE ITEMS & PLANNING ---
        "item_price": {"path": PurchaseOrderItem.unit_price, "label": "Unit Price", "group": "Commercial", "join_path": [PurchaseOrderItem]},
        "ord_qty": {"path": PurchaseOrderItem.quantity, "label": "Ordered Qty", "group": "Commercial", "join_path": [PurchaseOrderItem]},
        "sch_qty": {"path": POScheduleLine.quantity, "label": "Scheduled Qty", "group": "Planning", "join_path": [PurchaseOrderItem, POScheduleLine]},
        "prom_date": {"path": POScheduleLine.delivery_date, "label": "Promised Date", "group": "Planning", "join_path": [PurchaseOrderItem, POScheduleLine]},

        # --- GROUP: LOGISTICS & PACKING ---
        "ship_no": {"path": ShipmentHeader.shipment_number, "label": "Shipment #", "group": "Logistics", "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeader]},
        "carrier_id": {"path": PartnerMaster.partner_identifier, "label": "Carrier ID", "group": "Logistics", "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeader, PartnerMaster]},
        "ship_status": {
            "path": ShipmentStatusLookup.status_name, 
            "label": "Status", 
            "group": "Logistics", 
            "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeader, ShipmentStatusLookup],
            "formatter": "status_icon",
            "icon_rules": [
                {"value": "DRAFT", "icon": "inventory_2", "color": "grey"},
                {"value": "IN-TRANSIT", "icon": "ship", "color": "blue"},
                {"value": "DELIVERED", "icon": "task_alt", "color": "green"}
            ]
        },
        "m_bol": {"path": ShipmentHeader.master_bill_lading, "label": "M-BOL", "group": "Logistics", "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeader]},
        "eta": {"path": ShipmentHeader.estimated_arrival, "label": "ETA", "group": "Logistics", "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeader]},
        "shipped_qty": {"path": ShipmentItem.shipped_qty, "label": "Shipped Qty", "group": "Packing", "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentItem]},
        "cont_no": {"path": ShipmentContainer.container_number, "label": "Container #", "group": "Packing", "join_path": [PurchaseOrderItem, POScheduleLine, ShipmentHeader, ShipmentContainer]},
    },
    "default_columns": ["po_no", "vendor_name", "sku", "sch_qty", "prom_date", "ship_status", "eta"]
}