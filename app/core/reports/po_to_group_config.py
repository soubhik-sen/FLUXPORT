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
ForwarderPartner = aliased(PartnerMaster, name="forwarder_partner")
ShipmentHeaderJoin = (ShipmentHeader, POScheduleLine.shipment_header_id == ShipmentHeader.id)
ShipmentItemJoin = (ShipmentItem, ShipmentItem.po_schedule_line_id == POScheduleLine.id)
ShipmentContainerJoin = (ShipmentContainer, ShipmentContainer.shipment_header_id == ShipmentHeader.id)
ShipmentStatusJoin = (ShipmentStatusLookup, ShipmentHeader.status_id == ShipmentStatusLookup.id)

PO_TO_GROUP_REPORT_CONFIG = {
    "report_id": "po_to_group",
    "base_model": PurchaseOrderHeader,
    "group_metrics": [
        {"id": "rows", "label_key": "LBL_GROUP_ROWS", "type": "count_rows"},
        {"id": "qty", "label_key": "LBL_GROUP_QTY", "type": "sum", "field": "sch_qty"},
        {
            "id": "earliest",
            "label_key": "LBL_GROUP_EARLIEST",
            "type": "min_date",
            "field": "prom_date",
        },
    ],
    "fields": {
        # --- GROUP: PROCUREMENT ---
        "po_no": {
            "path": PurchaseOrderHeader.po_number,
            "label": "PO Number",
            "label_key": "LBL_PO_NUMBER",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "search",
            "sortable": True,
            "width": 210
        },
        "po_item_no": {
            "path": PurchaseOrderItem.item_number,
            "label": "Item #",
            "label_key": "LBL_ITEM_NO",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "numeric",
            "width": 90,
            "join_path": [PurchaseOrderItem]
        },
        "po_item_id": {
            "path": PurchaseOrderItem.id,
            "label": "PO Item ID",
            "group": "Planning",
            "is_filterable": False,
            "hidden": True,
            "join_path": [PurchaseOrderItem]
        },
        "po_date": {
            "path": PurchaseOrderHeader.created_at,
            "label": "Order Date",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "date_range",
            "sortable": True
        },
        "vendor_id": {
            "path": PurchaseOrderHeader.vendor_id,
            "label": "Vendor Id",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "numeric",
        },
        "company_id": {
            "path": PurchaseOrderHeader.company_id,
            "label": "Company Id",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "numeric",
            "hidden": True,
        },
        "forwarder_id": {
            "path": PurchaseOrderHeader.forwarder_id,
            "label": "Forwarder Id",
            "group": "Logistics",
            "is_filterable": False,
            "filter_type": "numeric",
        },
        "vendor_name": {
            "path": VendorPartner.legal_name,
            "label": "Vendor",
            "label_key": "LBL_VENDOR",
            "group": "Procurement",
            "is_filterable": True,
            "filter_type": "select",
            "width": 180,
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
            "label_key": "LBL_SKU",
            "group": "Product",
            "is_filterable": True,
            "filter_type": "search",
            "width": 140,
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
            "label_key": "LBL_SCHEDULED_QTY",
            "group": "Planning",
            "is_filterable": True,
            "filter_type": "numeric_range",
            "width": 120,
            "editable": True,
            "join_path": [PurchaseOrderItem, POScheduleLine]
        },
        "prom_date": {
            "path": POScheduleLine.delivery_date,
            "label": "Promised Date",
            "label_key": "LBL_PROMISED_DATE",
            "group": "Planning",
            "is_filterable": True,
            "filter_type": "date_range",
            "width": 130,
            "join_path": [PurchaseOrderItem, POScheduleLine]
        },
        "po_schedule_line_no": {
            "path": POScheduleLine.schedule_number,
            "label": "Schedule Line #",
            "label_key": "LBL_SCHEDULE_LINE_NO",
            "group": "Planning",
            "is_filterable": True,
            "filter_type": "numeric",
            "width": 120,
            "join_path": [PurchaseOrderItem, POScheduleLine]
        },
        "po_schedule_line_id": {
            "path": POScheduleLine.id,
            "label": "Schedule Line ID",
            "group": "Planning",
            "is_filterable": False,
            "hidden": True,
            "join_path": [PurchaseOrderItem, POScheduleLine]
        },
        "shipment_header_id": {
            "path": POScheduleLine.shipment_header_id,
            "label": "Shipment Header ID",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "numeric",
            "hidden": True,
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
        "carrier_partner_id": {
            "path": ShipmentHeader.carrier_id,
            "label": "Carrier Partner Id",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "numeric",
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
        "forwarder_code": {
            "path": ForwarderPartner.partner_identifier,
            "label": "Forwarder Code",
            "label_key": "LBL_FORWARDER_CODE",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "select",
            "width": 140,
            "join_path": [
                (ForwarderPartner, PurchaseOrderHeader.forwarder_id == ForwarderPartner.id)
            ]
        },
        "forwarder_trade_name": {
            "path": ForwarderPartner.trade_name,
            "label": "Forwarder Trade Name",
            "label_key": "LBL_FORWARDER_TRADE_NAME",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "select",
            "width": 180,
            "join_path": [
                (ForwarderPartner, PurchaseOrderHeader.forwarder_id == ForwarderPartner.id)
            ]
        },
        "ship_status": {
            "path": ShipmentStatusLookup.status_name,
            "label": "Status",
            "label_key": "LBL_STATUS",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "select",
            "width": 110,
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
            "label_key": "LBL_ETA",
            "group": "Logistics",
            "is_filterable": True,
            "filter_type": "date_range",
            "width": 110,
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
    "default_columns": [
        "po_no",
        "po_item_no",
        "po_schedule_line_no",
        "sch_qty",
        "ship_no",
        "vendor_name",
        "forwarder_code",
        "forwarder_trade_name",
        "sku",
        "prom_date",
        "ship_status",
        "eta",
    ]
}
