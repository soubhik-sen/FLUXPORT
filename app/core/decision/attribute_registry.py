from __future__ import annotations

from typing import TypedDict


class AttributeDefinition(TypedDict, total=False):
    type: str
    label: str
    source: str
    relation: str


ATTRIBUTE_REGISTRY: dict[str, dict[str, AttributeDefinition]] = {
    "PURCHASE_ORDER": {
        "po_number": {
            "type": "string",
            "label": "PO Number",
            "source": "po_header.po_number",
        },
        "order_date": {
            "type": "date",
            "label": "Order Date",
            "source": "po_header.order_date",
        },
        "total_value": {
            "type": "number",
            "label": "PO Amount",
            "source": "po_header.total_amount",
        },
        "currency": {
            "type": "string",
            "label": "Currency",
            "source": "po_header.currency",
        },
        "po_status": {
            "type": "string",
            "label": "PO Status Code",
            "source": "po_status_lookup.status_code",
        },
        "po_type": {
            "type": "string",
            "label": "PO Type Code",
            "source": "po_type_lookup.type_code",
        },
        "purchase_org": {
            "type": "string",
            "label": "Purchase Org Code",
            "source": "purchase_org_lookup.org_code",
        },
        "vendor_code": {
            "type": "string",
            "label": "Vendor Code",
            "source": "partner_master.partner_identifier",
            "relation": "vendor_id",
        },
        "vendor_name": {
            "type": "string",
            "label": "Vendor Name",
            "source": "partner_master.legal_name",
            "relation": "vendor_id",
        },
        "forwarder_code": {
            "type": "string",
            "label": "Forwarder Code",
            "source": "partner_master.partner_identifier",
            "relation": "forwarder_id",
        },
        "forwarder_name": {
            "type": "string",
            "label": "Forwarder Name",
            "source": "partner_master.legal_name",
            "relation": "forwarder_id",
        },
        "item_count": {
            "type": "number",
            "label": "Item Count",
            "source": "po_item.count",
        },
        "total_quantity": {
            "type": "number",
            "label": "Total Quantity",
            "source": "po_item.sum(quantity)",
        },
        "schedule_line_count": {
            "type": "number",
            "label": "Schedule Line Count",
            "source": "po_schedule_line.count",
        },
        "latest_delivery_date": {
            "type": "date",
            "label": "Latest Delivery Date",
            "source": "po_schedule_line.max(delivery_date)",
        },
        "is_overdue": {
            "type": "bool",
            "label": "Is Overdue",
            "source": "virtual.is_overdue",
        },
        "shipment_status": {
            "type": "string",
            "label": "Shipment Status",
            "source": "shipment_header.status_code",
            "relation": "po_id",
        },
        "vendor_score": {
            "type": "number",
            "label": "Vendor Rating",
            "source": "partner_master.vendor_score",
            "relation": "vendor_id",
        },
    },
    "SHIPMENT": {
        "shipment_number": {
            "type": "string",
            "label": "Shipment Number",
            "source": "shipment_header.shipment_number",
        },
        "shipment_status": {
            "type": "string",
            "label": "Shipment Status Code",
            "source": "shipment_status_lookup.status_code",
        },
        "shipment_type": {
            "type": "string",
            "label": "Shipment Type Code",
            "source": "ship_type_lookup.type_code",
        },
        "transport_mode": {
            "type": "string",
            "label": "Transport Mode Code",
            "source": "transport_mode_lookup.mode_code",
        },
        "carrier_code": {
            "type": "string",
            "label": "Carrier Code",
            "source": "partner_master.partner_identifier",
            "relation": "carrier_id",
        },
        "carrier_name": {
            "type": "string",
            "label": "Carrier Name",
            "source": "partner_master.legal_name",
            "relation": "carrier_id",
        },
        "pol_port_code": {
            "type": "string",
            "label": "POL Port Code",
            "source": "port_lookup.port_code",
            "relation": "pol_port_id",
        },
        "pod_port_code": {
            "type": "string",
            "label": "POD Port Code",
            "source": "port_lookup.port_code",
            "relation": "pod_port_id",
        },
        "external_reference": {
            "type": "string",
            "label": "External Reference",
            "source": "shipment_header.external_reference",
        },
        "master_bill_lading": {
            "type": "string",
            "label": "Master Bill Lading",
            "source": "shipment_header.master_bill_lading",
        },
        "estimated_departure": {
            "type": "date",
            "label": "Estimated Departure",
            "source": "shipment_header.estimated_departure",
        },
        "estimated_arrival": {
            "type": "date",
            "label": "Estimated Arrival",
            "source": "shipment_header.estimated_arrival",
        },
        "actual_arrival": {
            "type": "date",
            "label": "Actual Arrival",
            "source": "shipment_header.actual_arrival",
        },
        "item_count": {
            "type": "number",
            "label": "Shipment Item Count",
            "source": "shipment_item.count",
        },
        "total_shipped_qty": {
            "type": "number",
            "label": "Total Shipped Quantity",
            "source": "shipment_item.sum(shipped_qty)",
        },
        "container_count": {
            "type": "number",
            "label": "Container Count",
            "source": "shipment_container.count",
        },
        "milestone_count": {
            "type": "number",
            "label": "Milestone Count",
            "source": "shipment_milestone.count",
        },
        "is_delayed": {
            "type": "bool",
            "label": "Is Delayed",
            "source": "virtual.is_delayed",
        },
        "related_po_number": {
            "type": "string",
            "label": "Related PO Number",
            "source": "po_header.po_number",
            "relation": "po_schedule_line.po_item_id",
        },
    },
}


def get_attribute_registry(object_type: str) -> dict[str, AttributeDefinition]:
    key = (object_type or "").strip().upper()
    return ATTRIBUTE_REGISTRY.get(key, {})
