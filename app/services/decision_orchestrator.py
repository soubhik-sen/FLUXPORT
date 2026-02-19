from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.decision.attribute_registry import get_attribute_registry
from app.models.decision_history import DecisionHistory
from app.models.partner_master import PartnerMaster
from app.models.po_schedule_line import POScheduleLine
from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.models.shipment import (
    ShipmentHeader,
    ShipmentItem,
    ShipmentContainer,
    ShipmentMilestone,
)
from app.models.logistics_lookups import ShipmentStatusLookup, ShipTypeLookup
from app.services.decision_engine_client import evaluate as evaluate_decision

logger = logging.getLogger(__name__)


class DecisionOrchestrator:
    @staticmethod
    def trigger_evaluation(
        db: Session,
        object_id: int | str,
        object_type: str,
        table_slug: str,
        user_email: str | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any]:
        payload_json = "{}"
        normalized_object_type = (object_type or "").strip().upper()
        try:
            attributes = get_attribute_registry(normalized_object_type)
            if not attributes:
                raise ValueError(f"No attribute registry configured for object_type '{object_type}'.")

            raw_context = DecisionOrchestrator._hydrate_context(
                db=db,
                object_id=object_id,
                object_type=normalized_object_type,
                attributes=attributes,
            )
            context = DecisionOrchestrator._normalize_context_for_dispatch(
                context=raw_context,
                attributes=attributes,
            )
            safe_context = DecisionOrchestrator._json_safe(context)
            dispatch_payload = {
                "table_slug": table_slug,
                "context": safe_context,
                "object_id": str(object_id),
                "object_type": normalized_object_type,
            }
            payload_json = json.dumps(dispatch_payload, default=str)
        except Exception as exc:
            logger.warning(
                "Decision orchestration preparation failed for object_type=%s object_id=%s; proceeding without blocking. error=%s",
                object_type,
                object_id,
                exc,
            )
            DecisionOrchestrator._safe_log_decision(
                db=db,
                object_id=object_id,
                object_type=object_type,
                table_slug=table_slug,
                payload_json=payload_json,
                response_payload=None,
                status="FAILED",
                user_email=user_email,
                error_message=str(exc),
            )
            if raise_on_error:
                raise
            return {
                "status": "FAILED",
                "error": str(exc),
            }

        try:
            response_payload = evaluate_decision(
                dispatch_payload,
                timeout_seconds=10,
            )

            DecisionOrchestrator._safe_log_decision(
                db=db,
                object_id=object_id,
                object_type=object_type,
                table_slug=table_slug,
                payload_json=payload_json,
                response_payload=response_payload,
                status="SUCCESS",
                user_email=user_email,
            )
            return {
                "status": "SUCCESS",
                "response": response_payload,
            }
        except Exception as exc:
            logger.warning(
                "Decision service call failed for object_type=%s object_id=%s table_slug=%s; proceeding without blocking. error=%s",
                object_type,
                object_id,
                table_slug,
                exc,
            )
            DecisionOrchestrator._safe_log_decision(
                db=db,
                object_id=object_id,
                object_type=object_type,
                table_slug=table_slug,
                payload_json=payload_json,
                response_payload=None,
                status="FAILED",
                error_message=str(exc),
                user_email=user_email,
            )
            if raise_on_error:
                raise
            return {
                "status": "FAILED",
                "error": str(exc),
            }

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): DecisionOrchestrator._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [DecisionOrchestrator._json_safe(v) for v in value]
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    @staticmethod
    def _normalize_context_for_dispatch(
        context: dict[str, Any],
        attributes: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, meta in attributes.items():
            value = context.get(key)
            attr_type = (meta or {}).get("type")
            if attr_type == "string":
                if value is None:
                    normalized[key] = " "
                    continue
                if isinstance(value, str) and value.strip() == "":
                    normalized[key] = " "
                    continue
            normalized[key] = value
        return normalized

    @staticmethod
    def _safe_log_decision(
        db: Session,
        object_id: int | str,
        object_type: str,
        table_slug: str,
        payload_json: str,
        response_payload: dict[str, Any] | None,
        status: str,
        user_email: str | None,
        error_message: str | None = None,
    ) -> None:
        try:
            DecisionOrchestrator._log_decision(
                db=db,
                object_id=object_id,
                object_type=object_type,
                table_slug=table_slug,
                payload_json=payload_json,
                response_payload=response_payload,
                status=status,
                user_email=user_email,
                error_message=error_message,
            )
        except Exception as exc:
            db.rollback()
            logger.warning(
                "Decision history persistence failed for object_type=%s object_id=%s table_slug=%s; request flow continues. error=%s",
                object_type,
                object_id,
                table_slug,
                exc,
            )

    @staticmethod
    def _hydrate_context(
        db: Session,
        object_id: int | str,
        object_type: str,
        attributes: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        normalized = (object_type or "").strip().upper()
        if normalized == "PURCHASE_ORDER":
            return DecisionOrchestrator._hydrate_purchase_order(db, int(object_id), attributes)
        if normalized == "SHIPMENT":
            return DecisionOrchestrator._hydrate_shipment(db, int(object_id), attributes)
        raise ValueError(f"Hydration not supported for object_type '{object_type}'.")

    @staticmethod
    def _hydrate_purchase_order(
        db: Session,
        po_id: int,
        attributes: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        po = db.query(PurchaseOrderHeader).filter(PurchaseOrderHeader.id == po_id).first()
        if not po:
            raise ValueError(f"Purchase Order {po_id} not found.")

        context: dict[str, Any] = {}
        for key in attributes.keys():
            context[key] = DecisionOrchestrator._resolve_po_attribute(db, po, key)
        return context

    @staticmethod
    def _hydrate_shipment(
        db: Session,
        shipment_id: int,
        attributes: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        shipment = db.query(ShipmentHeader).filter(ShipmentHeader.id == shipment_id).first()
        if not shipment:
            raise ValueError(f"Shipment {shipment_id} not found.")

        context: dict[str, Any] = {}
        for key in attributes.keys():
            context[key] = DecisionOrchestrator._resolve_shipment_attribute(db, shipment, key)
        return context

    @staticmethod
    def _resolve_po_attribute(db: Session, po: PurchaseOrderHeader, attr_key: str) -> Any:
        if attr_key == "po_number":
            return po.po_number
        if attr_key == "order_date":
            return po.order_date
        if attr_key == "total_value":
            return float(po.total_amount or 0)
        if attr_key == "currency":
            return po.currency
        if attr_key == "po_status":
            status = po.status
            return status.status_code if status is not None else None
        if attr_key == "po_type":
            doc_type = po.doc_type
            return doc_type.type_code if doc_type is not None else None
        if attr_key == "purchase_org":
            purchase_org = po.purchase_org
            return purchase_org.org_code if purchase_org is not None else None
        if attr_key == "vendor_code":
            return DecisionOrchestrator._resolve_partner_identifier(db, po.vendor_id)
        if attr_key == "vendor_name":
            return DecisionOrchestrator._resolve_partner_name(db, po.vendor_id)
        if attr_key == "forwarder_code":
            return DecisionOrchestrator._resolve_partner_identifier(db, po.forwarder_id)
        if attr_key == "forwarder_name":
            return DecisionOrchestrator._resolve_partner_name(db, po.forwarder_id)
        if attr_key == "item_count":
            return (
                db.query(func.count(PurchaseOrderItem.id))
                .filter(PurchaseOrderItem.po_header_id == po.id)
                .scalar()
            ) or 0
        if attr_key == "total_quantity":
            total_qty = (
                db.query(func.sum(PurchaseOrderItem.quantity))
                .filter(PurchaseOrderItem.po_header_id == po.id)
                .scalar()
            )
            return float(total_qty or 0)
        if attr_key == "schedule_line_count":
            return (
                db.query(func.count(POScheduleLine.id))
                .join(PurchaseOrderItem, PurchaseOrderItem.id == POScheduleLine.po_item_id)
                .filter(PurchaseOrderItem.po_header_id == po.id)
                .scalar()
            ) or 0
        if attr_key == "latest_delivery_date":
            return (
                db.query(func.max(POScheduleLine.delivery_date))
                .join(PurchaseOrderItem, PurchaseOrderItem.id == POScheduleLine.po_item_id)
                .filter(PurchaseOrderItem.po_header_id == po.id)
                .scalar()
            )
        if attr_key == "is_overdue":
            today = date.today()
            overdue = (
                db.query(func.count(POScheduleLine.id))
                .join(PurchaseOrderItem, PurchaseOrderItem.id == POScheduleLine.po_item_id)
                .filter(PurchaseOrderItem.po_header_id == po.id)
                .filter(POScheduleLine.delivery_date < today)
                .filter(POScheduleLine.received_qty < POScheduleLine.quantity)
                .scalar()
            )
            return bool(overdue)
        if attr_key == "shipment_status":
            return DecisionOrchestrator._resolve_po_shipment_status(db, po.id)
        if attr_key == "vendor_score":
            return DecisionOrchestrator._resolve_vendor_score(db, po.vendor_id)
        return None

    @staticmethod
    def _resolve_shipment_attribute(
        db: Session,
        shipment: ShipmentHeader,
        attr_key: str,
    ) -> Any:
        if attr_key == "shipment_number":
            return shipment.shipment_number
        if attr_key == "shipment_status":
            status = shipment.status
            return status.status_code if status is not None else None
        if attr_key == "shipment_type":
            row = (
                db.query(ShipTypeLookup.type_code)
                .filter(ShipTypeLookup.id == shipment.type_id)
                .first()
            )
            return row[0] if row else None
        if attr_key == "transport_mode":
            mode = shipment.transport_mode
            return mode.mode_code if mode is not None else None
        if attr_key == "carrier_code":
            return DecisionOrchestrator._resolve_partner_identifier(db, shipment.carrier_id)
        if attr_key == "carrier_name":
            return DecisionOrchestrator._resolve_partner_name(db, shipment.carrier_id)
        if attr_key == "pol_port_code":
            return shipment.pol_port.port_code if shipment.pol_port is not None else None
        if attr_key == "pod_port_code":
            return shipment.pod_port.port_code if shipment.pod_port is not None else None
        if attr_key == "external_reference":
            return shipment.external_reference
        if attr_key == "master_bill_lading":
            return shipment.master_bill_lading
        if attr_key == "estimated_departure":
            return shipment.estimated_departure
        if attr_key == "estimated_arrival":
            return shipment.estimated_arrival
        if attr_key == "actual_arrival":
            return shipment.actual_arrival
        if attr_key == "item_count":
            return (
                db.query(func.count(ShipmentItem.id))
                .filter(ShipmentItem.shipment_header_id == shipment.id)
                .scalar()
            ) or 0
        if attr_key == "total_shipped_qty":
            total_qty = (
                db.query(func.sum(ShipmentItem.shipped_qty))
                .filter(ShipmentItem.shipment_header_id == shipment.id)
                .scalar()
            )
            return float(total_qty or 0)
        if attr_key == "container_count":
            return (
                db.query(func.count(ShipmentContainer.id))
                .filter(ShipmentContainer.shipment_header_id == shipment.id)
                .scalar()
            ) or 0
        if attr_key == "milestone_count":
            return (
                db.query(func.count(ShipmentMilestone.id))
                .filter(ShipmentMilestone.shipment_header_id == shipment.id)
                .scalar()
            ) or 0
        if attr_key == "is_delayed":
            eta = shipment.estimated_arrival
            ata = shipment.actual_arrival
            if ata is not None and eta is not None:
                return ata > eta
            if ata is None and eta is not None:
                return date.today() > eta
            return False
        if attr_key == "related_po_number":
            row = (
                db.query(PurchaseOrderHeader.po_number)
                .join(PurchaseOrderItem, PurchaseOrderItem.po_header_id == PurchaseOrderHeader.id)
                .join(POScheduleLine, POScheduleLine.po_item_id == PurchaseOrderItem.id)
                .filter(POScheduleLine.shipment_header_id == shipment.id)
                .order_by(PurchaseOrderHeader.id.asc())
                .first()
            )
            return row[0] if row else None
        return None

    @staticmethod
    def _resolve_po_shipment_status(db: Session, po_id: int) -> str | None:
        row = (
            db.query(ShipmentStatusLookup.status_code)
            .join(ShipmentHeader, ShipmentHeader.status_id == ShipmentStatusLookup.id)
            .join(POScheduleLine, POScheduleLine.shipment_header_id == ShipmentHeader.id)
            .join(PurchaseOrderItem, PurchaseOrderItem.id == POScheduleLine.po_item_id)
            .filter(PurchaseOrderItem.po_header_id == po_id)
            .order_by(ShipmentHeader.id.desc())
            .first()
        )
        return row[0] if row else None

    @staticmethod
    def _resolve_vendor_score(db: Session, vendor_id: int | None) -> float | None:
        if vendor_id is None:
            return None
        vendor = db.query(PartnerMaster).filter(PartnerMaster.id == vendor_id).first()
        if not vendor:
            return None
        return 100.0 if vendor.is_verified else 0.0

    @staticmethod
    def _resolve_partner_identifier(db: Session, partner_id: int | None) -> str | None:
        if partner_id is None:
            return None
        partner = db.query(PartnerMaster).filter(PartnerMaster.id == partner_id).first()
        if not partner:
            return None
        return partner.partner_identifier

    @staticmethod
    def _resolve_partner_name(db: Session, partner_id: int | None) -> str | None:
        if partner_id is None:
            return None
        partner = db.query(PartnerMaster).filter(PartnerMaster.id == partner_id).first()
        if not partner:
            return None
        return partner.trade_name or partner.legal_name

    @staticmethod
    def _log_decision(
        db: Session,
        object_id: int | str,
        object_type: str,
        table_slug: str,
        payload_json: str,
        response_payload: dict[str, Any] | None,
        status: str,
        user_email: str | None,
        error_message: str | None = None,
    ) -> None:
        rule_id = None
        result_summary = None
        response_json = None
        if response_payload is not None:
            response_json = json.dumps(response_payload, default=str)
            if isinstance(response_payload, dict):
                rule_id = response_payload.get("rule_id")
                result = response_payload.get("result")
                if result is not None:
                    result_summary = json.dumps(result, default=str)

        entry = DecisionHistory(
            object_type=(object_type or "").strip().upper(),
            object_id=str(object_id),
            table_slug=table_slug,
            payload_json=payload_json,
            response_json=response_json,
            rule_id=rule_id,
            result_summary=result_summary,
            status=status,
            error_message=error_message,
            created_by=user_email or "system@local",
            last_changed_by=user_email or "system@local",
        )
        db.add(entry)
        db.commit()
