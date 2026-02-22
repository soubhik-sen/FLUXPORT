from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from app.db.session import get_db
from app.schemas.shipment import (
    ShipmentHeaderCreate,
    ShipmentHeader as ShipmentHeaderSchema,
    ShipmentItemCreate,
    ShipmentFromScheduleLinesRequest,
    ShipmentSplitLine,
    ShipmentHeaderSummary,
    ShipmentWorkspaceResponse,
    ShipmentWorkspaceHeader,
    ShipmentWorkspaceItem,
    ShipmentWorkspaceMilestone,
    ShipmentWorkspaceDocument,
    ShipmentWorkspaceContainer,
    ShipmentWorkspaceText,
)
from app.schemas.text_profile import (
    RuntimeTextRowOut,
    RuntimeTextsUpdateRequest,
    RuntimeTextsUpdateResponse,
    ShipmentTextProfileResolveRequest,
    TextProfileResolveResponse,
)
from app.services.logistics_service import LogisticsService
from app.services.decision_orchestrator import DecisionOrchestrator
from app.services.role_scope_policy import (
    is_scope_denied,
    resolve_scope_by_field,
    scope_deny_detail,
    sanitize_scope_by_field,
)
from app.core.config import settings
from app.models.customer_master import CustomerMaster
from app.models.po_schedule_line import POScheduleLine
from app.models.purchase_order import PurchaseOrderItem, PurchaseOrderHeader
from app.models.product_master import ProductMaster
from app.models.logistics_lookups import (
    ShipmentStatusLookup,
    TransportModeLookup,
    ShipTypeLookup,
    MilestoneTypeLookup,
    ContainerTypeLookup,
)
from app.models.shipment import ShipmentHeader as ShipmentHeaderModel
from app.models.shipment import ShipmentItem as ShipmentItemModel
from app.models.shipment import ShipmentMilestone, ShipmentContainer
from app.models.partner_master import PartnerMaster
from app.models.document import DocumentAttachment
from app.models.doc_lookups import DocumentTypeLookup
from app.models.text_master import TextMaster
from app.models.text_lookups import TextTypeLookup
from app.models.doc_text import DocText, TextVal
from sqlalchemy.orm import aliased
from sqlalchemy import and_, or_
from app.api.deps.request_identity import get_request_email
from app.services.text_profile_service import TextProfileService
from app.services.document_lock_service import (
    DocumentLockFailure,
    DocumentLockService,
    LOCK_TOKEN_HEADER,
)
from app.core.flow_logging import flow_info

router = APIRouter()
logger = logging.getLogger(__name__)

def _get_user_email(request: Request) -> str:
    return get_request_email(request)

def _resolve_grouping_scope(db: Session, user_email: str) -> dict[str, set[int]]:
    return resolve_scope_by_field(
        db,
        user_email=user_email,
        endpoint_key="shipments.from_schedule_lines",
        http_method="POST",
        endpoint_path="/api/v1/shipments/from-schedule-lines",
    )


def _resolve_shipment_scope(
    db: Session,
    user_email: str,
    *,
    endpoint_key: str,
    http_method: str,
    endpoint_path: str,
) -> dict[str, set[int]]:
    return resolve_scope_by_field(
        db,
        user_email=user_email,
        endpoint_key=endpoint_key,
        http_method=http_method,
        endpoint_path=endpoint_path,
    )


def _scope_matches_po_header(
    header: PurchaseOrderHeader,
    scope_by_field: dict[str, set[int]],
    *,
    legacy_customer_company_ids: set[int] | None = None,
) -> bool:
    if not scope_by_field:
        return True
    for field_name, scoped_ids in scope_by_field.items():
        if not scoped_ids:
            continue
        if field_name == "customer_id":
            if header.customer_id in scoped_ids:
                return True
            if (
                header.customer_id is None
                and legacy_customer_company_ids
                and header.company_id in legacy_customer_company_ids
            ):
                return True
            continue
        if getattr(header, field_name, None) in scoped_ids:
            return True
    return False


def _legacy_company_ids_for_customer_scope(
    db: Session,
    scope_by_field: dict[str, set[int]],
) -> set[int]:
    customer_ids = scope_by_field.get("customer_id") or set()
    if not customer_ids:
        return set()
    rows = (
        db.query(CustomerMaster.company_id)
        .filter(CustomerMaster.id.in_(sorted(customer_ids)))
        .filter(CustomerMaster.company_id.isnot(None))
        .all()
    )
    return {int(row[0]) for row in rows if row and row[0] is not None}


def _shipment_ids_in_scope(
    db: Session,
    scope_by_field: dict[str, set[int]],
) -> set[int]:
    if not scope_by_field:
        rows = db.query(ShipmentHeaderModel.id).all()
        return {int(r[0]) for r in rows if r and r[0] is not None}

    clauses = []
    legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)
    for field_name, scoped_ids in scope_by_field.items():
        if not scoped_ids:
            continue
        if field_name == "customer_id":
            clauses.append(PurchaseOrderHeader.customer_id.in_(sorted(scoped_ids)))
            if legacy_customer_company_ids:
                clauses.append(
                    and_(
                        PurchaseOrderHeader.customer_id.is_(None),
                        PurchaseOrderHeader.company_id.in_(
                            sorted(legacy_customer_company_ids)
                        ),
                    )
                )
            continue
        column = getattr(PurchaseOrderHeader, field_name, None)
        if column is None:
            continue
        clauses.append(column.in_(sorted(scoped_ids)))
    if not clauses:
        return set()

    rows = (
        db.query(ShipmentItemModel.shipment_header_id)
        .join(PurchaseOrderItem, PurchaseOrderItem.id == ShipmentItemModel.po_item_id)
        .join(PurchaseOrderHeader, PurchaseOrderHeader.id == PurchaseOrderItem.po_header_id)
        .filter(ShipmentItemModel.shipment_header_id.isnot(None))
        .filter(or_(*clauses))
        .distinct()
        .all()
    )
    return {int(r[0]) for r in rows if r and r[0] is not None}


def _shipment_is_in_scope(
    db: Session,
    shipment_id: int,
    scope_by_field: dict[str, set[int]],
) -> bool:
    if not scope_by_field:
        return True
    return shipment_id in _shipment_ids_in_scope(db, scope_by_field)


def _is_scope_values_allowed(
    scope_by_field: dict[str, set[int]],
    values_by_field: dict[str, int | None],
) -> bool:
    if not scope_by_field:
        return True

    relevant = {
        field_name: ids
        for field_name, ids in scope_by_field.items()
        if field_name in {"customer_id", "company_id", "vendor_id", "forwarder_id"} and ids
    }
    if not relevant:
        return True

    matched = False
    for field_name, scoped_ids in relevant.items():
        value = values_by_field.get(field_name)
        if value is None:
            continue
        if value not in scoped_ids:
            return False
        matched = True
    return matched


def _runtime_text_to_out(row) -> RuntimeTextRowOut:
    text_type = row.text_type
    return RuntimeTextRowOut(
        id=int(row.id),
        source="runtime",
        text_type_id=int(row.text_type_id),
        text_type_code=text_type.text_type_code if text_type else None,
        text_type_name=text_type.text_type_name if text_type else None,
        language=row.language,
        text_value=row.text_value,
        is_editable=True,
        is_mandatory=False,
        is_user_edited=bool(getattr(row, "is_user_edited", False)),
        profile_id=row.profile_id,
        profile_version=row.profile_version,
    )

def _normalize_idempotency_key(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    key = raw_value.strip()
    if not key:
        return None
    normalized = "".join(ch for ch in key if ch.isalnum() or ch in ("-", "_"))
    if not normalized:
        return None
    return normalized[:40]

def _idempotency_reference(key: str) -> str:
    return f"IDEMP:{key}"


def _resolve_lookup_id(db: Session, model, code_field: str, preferred_codes: List[str]) -> int:
    for code in preferred_codes:
        row = db.query(model).filter(
            getattr(model, code_field) == code,
            model.is_active == True
        ).first()
        if row:
            return row.id
    row = db.query(model).filter(model.is_active == True).order_by(model.id.asc()).first()
    if not row:
        raise HTTPException(status_code=400, detail=f"No active {model.__tablename__} configured.")
    return row.id


def _default_ship_type_id(db: Session) -> int:
    return _resolve_lookup_id(db, ShipTypeLookup, "type_code", ["STD", "STANDARD"])


def _default_status_id(db: Session) -> int:
    return _resolve_lookup_id(db, ShipmentStatusLookup, "status_code", ["BOOKED", "PLANNED", "DRAFT"])


def _default_mode_id(db: Session) -> int:
    return _resolve_lookup_id(db, TransportModeLookup, "mode_code", ["SEA", "AIR", "ROAD", "RAIL"])

@router.post("/", 
             response_model=ShipmentHeaderSchema, 
             status_code=status.HTTP_201_CREATED,
             summary="Execute a Shipment",
             description="Creates a shipment and links it to PO items. Validates remaining fulfillment quantities.")
def create_shipment(
    *,
    db: Session = Depends(get_db),
    request: Request,
    shipment_in: ShipmentHeaderCreate
):
    """
    Controller for Logistics Execution.
    The LogisticsService handles the critical cross-check between POs and Shipments.
    """
    user_email = _get_user_email(request)
    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.create",
        http_method="POST",
        endpoint_path="/api/v1/shipments",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)

    if scope_by_field:
        po_item_ids = sorted(
            {
                int(item.po_item_id)
                for item in (shipment_in.items or [])
                if item.po_item_id is not None
            }
        )
        if not po_item_ids:
            raise HTTPException(
                status_code=403,
                detail="Shipment payload is outside user scope.",
            )
        item_rows = (
            db.query(PurchaseOrderItem.id, PurchaseOrderHeader)
            .join(PurchaseOrderHeader, PurchaseOrderHeader.id == PurchaseOrderItem.po_header_id)
            .filter(PurchaseOrderItem.id.in_(po_item_ids))
            .all()
        )
        header_by_item_id = {int(item_id): header for item_id, header in item_rows}
        forbidden_item_ids: list[int] = []
        for po_item_id in po_item_ids:
            header = header_by_item_id.get(po_item_id)
            if header is None or not _scope_matches_po_header(
                header,
                scope_by_field,
                legacy_customer_company_ids=legacy_customer_company_ids,
            ):
                forbidden_item_ids.append(po_item_id)
        if forbidden_item_ids:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Shipment payload is outside user scope.",
                    "forbidden_po_item_ids": sorted(forbidden_item_ids),
                    "scope_keys": sorted(scope_by_field.keys()),
                },
            )

    shipment_in = shipment_in.model_copy(update={"created_by": user_email, "last_changed_by": user_email})
    created_shipment = LogisticsService.create_shipment_with_validation(
        db=db,
        shipment_in=shipment_in,
        user_email=user_email,
    )
    DecisionOrchestrator.trigger_evaluation(
        db=db,
        object_id=created_shipment.id,
        object_type="SHIPMENT",
        table_slug="shipment",
        user_email=user_email,
        raise_on_error=False,
    )
    if settings.TEXT_PROFILE_ENABLED and shipment_in.texts:
        TextProfileService.upsert_shipment_runtime_texts(
            db,
            shipment_id=int(created_shipment.id),
            rows=[row.model_dump() for row in shipment_in.texts],
            user_email=user_email,
            profile_id=shipment_in.text_profile_id,
            profile_version=shipment_in.text_profile_version,
            mark_user_edited=False,
        )
        db.commit()
    return created_shipment


@router.post(
    "/text-profile/resolve",
    response_model=TextProfileResolveResponse,
    summary="Resolve initial shipment text profile and text values",
)
def resolve_shipment_text_profile(
    payload: ShipmentTextProfileResolveRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    if not settings.TEXT_PROFILE_ENABLED:
        resolved = TextProfileService.resolve_shipment_text_profile_default(
            db,
            user_email=user_email,
            language_override=payload.locale_override_language,
            country_override=payload.locale_override_country,
            preferred_profile_name="shipment_text_profile",
        )
        return TextProfileResolveResponse(
            profile_id=resolved.profile_id,
            profile_name=resolved.profile_name,
            profile_version=resolved.profile_version,
            language=resolved.language,
            country_code=resolved.country_code,
            source=resolved.source,
            texts=[
                RuntimeTextRowOut(
                    id=0,
                    source=row.source,
                    text_type_id=row.text_type_id,
                    text_type_code=row.text_type_code,
                    text_type_name=row.text_type_name,
                    language=row.language,
                    text_value=row.text_value,
                    is_editable=row.is_editable,
                    is_mandatory=row.is_mandatory,
                    is_user_edited=False,
                    profile_id=resolved.profile_id,
                    profile_version=resolved.profile_version,
                )
                for row in resolved.texts
            ],
        )

    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.text_profile.resolve",
        http_method="POST",
        endpoint_path="/api/v1/shipments/text-profile/resolve",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    resolved_company_id: int | None = payload.company_id
    if payload.customer_id is not None:
        customer = db.query(CustomerMaster).filter(CustomerMaster.id == payload.customer_id).first()
        if customer is None:
            raise HTTPException(status_code=400, detail="Invalid customer_id for text resolve")
        resolved_company_id = customer.company_id
    if not _is_scope_values_allowed(
        scope_by_field,
        {
            "customer_id": payload.customer_id,
            "company_id": resolved_company_id,
            "vendor_id": payload.vendor_id,
            "forwarder_id": payload.forwarder_id,
        },
    ):
        raise HTTPException(status_code=403, detail="Text profile resolve payload is outside user scope")

    resolved = TextProfileService.resolve_shipment_text_profile(
        db,
        user_email=user_email,
        context={
            "type_id": payload.type_id,
            "status_id": payload.status_id,
            "mode_id": payload.mode_id,
            "carrier_id": payload.carrier_id,
            "customer_id": payload.customer_id,
            "company_id": resolved_company_id,
            "vendor_id": payload.vendor_id,
            "forwarder_id": payload.forwarder_id,
            "estimated_departure": payload.estimated_departure.isoformat()
            if payload.estimated_departure
            else None,
            "estimated_arrival": payload.estimated_arrival.isoformat()
            if payload.estimated_arrival
            else None,
        },
        language_override=payload.locale_override_language,
        country_override=payload.locale_override_country,
    )
    return TextProfileResolveResponse(
        profile_id=resolved.profile_id,
        profile_name=resolved.profile_name,
        profile_version=resolved.profile_version,
        language=resolved.language,
        country_code=resolved.country_code,
        source=resolved.source,
        texts=[
            RuntimeTextRowOut(
                id=0,
                source=row.source,
                text_type_id=row.text_type_id,
                text_type_code=row.text_type_code,
                text_type_name=row.text_type_name,
                language=row.language,
                text_value=row.text_value,
                is_editable=row.is_editable,
                is_mandatory=row.is_mandatory,
                is_user_edited=False,
                profile_id=resolved.profile_id,
                profile_version=resolved.profile_version,
            )
            for row in resolved.texts
        ],
    )


@router.post(
    "/from_schedule_lines",
    response_model=ShipmentHeaderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create shipment from schedule lines",
)
def create_shipment_from_schedule_lines(
    *,
    db: Session = Depends(get_db),
    request: Request,
    payload: ShipmentFromScheduleLinesRequest,
):
    user_email = _get_user_email(request)
    flow_info(
        logger,
        "shipment_finalize_requested user=%s schedule_line_ids_count=%s lines_count=%s",
        user_email,
        len(payload.schedule_line_ids or []),
        len(payload.lines or []),
        category="shipment",
    )
    idempotency_key = _normalize_idempotency_key(
        request.headers.get("Idempotency-Key")
    )
    idempotency_ref = (
        _idempotency_reference(idempotency_key) if idempotency_key is not None else None
    )
    if idempotency_ref is not None:
        existing = (
            db.query(ShipmentHeaderModel)
            .filter(ShipmentHeaderModel.external_reference == idempotency_ref)
            .filter(ShipmentHeaderModel.created_by == user_email)
            .order_by(ShipmentHeaderModel.id.desc())
            .first()
        )
        if existing is not None:
            flow_info(
                logger,
                "shipment_finalize_idempotent_hit user=%s shipment_id=%s idempotency_ref=%s",
                user_email,
                existing.id,
                idempotency_ref,
                category="shipment",
            )
            return existing

    def _as_float(value) -> float:
        return float(value)

    schedule_line_ids = payload.schedule_line_ids or []
    lines = payload.lines or []
    if not schedule_line_ids and not lines:
        flow_info(
            logger,
            "shipment_finalize_invalid_input user=%s reason=no_schedule_lines",
            user_email,
            category="shipment",
        )
        raise HTTPException(
            status_code=400,
            detail="Provide schedule_line_ids or lines.",
        )
    if lines:
        schedule_line_ids = [l.schedule_line_id for l in lines]

    # Fetch schedule lines with PO item + header
    schedule_lines = (
        db.query(POScheduleLine)
        .join(PurchaseOrderItem, POScheduleLine.po_item_id == PurchaseOrderItem.id)
        .filter(POScheduleLine.id.in_(schedule_line_ids))
        .with_for_update()
        .all()
    )
    line_by_id = {line.id: line for line in schedule_lines}
    found_ids = {line.id for line in schedule_lines}
    missing = [sid for sid in schedule_line_ids if sid not in found_ids]
    if missing:
        flow_info(
            logger,
            "shipment_finalize_missing_schedule_lines user=%s missing_ids=%s",
            user_email,
            missing,
            category="shipment",
        )
        raise HTTPException(status_code=404, detail={"missing_schedule_line_ids": missing})

    # Enforce union scope across forwarder/supplier/customer mappings.
    raw_scope = _resolve_grouping_scope(db, user_email)
    if is_scope_denied(raw_scope):
        flow_info(
            logger,
            "shipment_finalize_scope_denied user=%s reason=%s",
            user_email,
            scope_deny_detail(raw_scope),
            category="shipment",
        )
        raise HTTPException(
            status_code=403,
            detail={"error": scope_deny_detail(raw_scope)},
        )
    scope_by_field = sanitize_scope_by_field(raw_scope)
    if scope_by_field:
        legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(
            db, scope_by_field
        )
        forbidden_ids: list[int] = []
        for line in schedule_lines:
            header = line.item.header if line.item is not None else None
            if header is None:
                forbidden_ids.append(line.id)
                continue
            in_scope = _scope_matches_po_header(
                header,
                scope_by_field,
                legacy_customer_company_ids=legacy_customer_company_ids,
            )
            if not in_scope:
                forbidden_ids.append(line.id)
        if forbidden_ids:
            flow_info(
                logger,
                "shipment_finalize_out_of_scope user=%s forbidden_schedule_line_ids=%s scope_keys=%s",
                user_email,
                sorted(forbidden_ids),
                sorted(scope_by_field.keys()),
                category="shipment",
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Selected schedule lines are outside user scope.",
                    "scope_keys": sorted(scope_by_field.keys()),
                    "forbidden_schedule_line_ids": sorted(forbidden_ids),
                },
            )

    # Determine carrier from PO header forwarder_id
    carrier_ids = set()
    for line in schedule_lines:
        if line.item is None or line.item.header is None:
            continue
        if line.item.header.forwarder_id is not None:
            carrier_ids.add(line.item.header.forwarder_id)

    if len(carrier_ids) != 1:
        flow_info(
            logger,
            "shipment_finalize_invalid_carrier_set user=%s carrier_ids=%s",
            user_email,
            sorted(carrier_ids),
            category="shipment",
        )
        raise HTTPException(
            status_code=400,
            detail="Selected schedule lines must have a single forwarder/carrier."
        )
    carrier_id = carrier_ids.pop()

    # Defaults
    type_id = _default_ship_type_id(db)
    status_id = _default_status_id(db)
    mode_id = _default_mode_id(db)

    items: List[ShipmentItemCreate] = []
    if lines:
        # Group splits by parent schedule line
        grouped: dict[int, list[ShipmentSplitLine]] = {}
        for entry in lines:
            grouped.setdefault(entry.schedule_line_id, []).append(entry)

        for schedule_id, split_entries in grouped.items():
            parent_line = line_by_id.get(schedule_id)
            if parent_line is None:
                continue
            if parent_line.shipment_header_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Schedule line {schedule_id} is already linked to "
                        f"shipment header {parent_line.shipment_header_id}."
                    ),
                )

            original_qty = _as_float(parent_line.quantity)
            split_total = sum(_as_float(entry.qty) for entry in split_entries)
            if abs(split_total - original_qty) > 0.001:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Split total mismatch for schedule line {schedule_id}: "
                        f"expected {original_qty:.3f}, got {split_total:.3f}."
                    ),
                )
            if split_total <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid non-positive split total for schedule line {schedule_id}.",
                )

            seen_split_ids = set()
            for entry in split_entries:
                qty = _as_float(entry.qty)
                if qty <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Split line for schedule line {schedule_id} has non-positive qty {qty:.3f}."
                        ),
                    )
                if entry.split_line_id:
                    if entry.split_line_id in seen_split_ids:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Duplicate split_line_id '{entry.split_line_id}' "
                                f"for schedule line {schedule_id}."
                            ),
                        )
                    seen_split_ids.add(entry.split_line_id)

            # Sort by split_line_id if present
            def _split_sort_key(s: ShipmentSplitLine):
                try:
                    return int(s.split_line_id or "1")
                except ValueError:
                    return 1
            split_entries.sort(key=_split_sort_key)

            parent_entry = None
            for entry in split_entries:
                if entry.schedule_line_no is not None and entry.schedule_line_no == parent_line.schedule_number:
                    parent_entry = entry
                    break
            if parent_entry is None:
                parent_entry = split_entries[0]

            # Update parent schedule line to parent entry qty
            parent_line.quantity = parent_entry.qty
            db.add(parent_line)

            # Determine next schedule_number for this PO item (avoid duplicates)
            existing_rows = db.query(
                POScheduleLine.id, POScheduleLine.schedule_number
            ).filter(
                POScheduleLine.po_item_id == parent_line.po_item_id
            ).all()
            used_numbers = {row.schedule_number for row in existing_rows if row.schedule_number is not None}
            max_sched = max(used_numbers) if used_numbers else 0
            next_sched = max_sched + 1

            split_line_id_map: dict[str | None, int] = {parent_entry.split_line_id: parent_line.id}

            # Create additional schedule lines for splits beyond parent entry
            for split in split_entries:
                if split is parent_entry:
                    continue
                schedule_no = split.schedule_line_no
                if schedule_no is None or schedule_no <= 0:
                    schedule_no = next_sched
                # Ensure uniqueness within the PO item
                if schedule_no in used_numbers:
                    schedule_no = next_sched
                while schedule_no in used_numbers:
                    schedule_no += 1
                if schedule_no >= next_sched:
                    next_sched = schedule_no + 1
                used_numbers.add(schedule_no)
                new_line = POScheduleLine(
                    po_item_id=parent_line.po_item_id,
                    shipment_header_id=None,
                    schedule_number=schedule_no,
                    quantity=split.qty,
                    received_qty=0,
                    delivery_date=parent_line.delivery_date,
                )
                db.add(new_line)
                db.flush()
                split_line_id_map[split.split_line_id] = new_line.id

            # Create shipment items only for selected splits
            for split in split_entries:
                if split.ship is False:
                    continue
                target_id = split_line_id_map.get(split.split_line_id)
                if target_id is None:
                    continue
                items.append(
                    ShipmentItemCreate(
                        po_item_id=parent_line.po_item_id,
                        po_schedule_line_id=target_id,
                        shipped_qty=split.qty,
                        package_id=None,
                        gross_weight=None,
                    )
                )
        db.flush()
    else:
        for line in schedule_lines:
            if line.shipment_header_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Schedule line {line.id} is already linked to "
                        f"shipment header {line.shipment_header_id}."
                    ),
                )
            items.append(
                ShipmentItemCreate(
                    po_item_id=line.po_item_id,
                    po_schedule_line_id=line.id,
                    shipped_qty=line.quantity,
                    package_id=None,
                    gross_weight=None,
                )
            )

    if not items:
        flow_info(logger, "shipment_finalize_no_items user=%s", user_email, category="shipment")
        raise HTTPException(
            status_code=400,
            detail="No lines marked for shipment.",
        )

    shipment_in = ShipmentHeaderCreate(
        shipment_number=None,
        external_reference=idempotency_ref,
        type_id=type_id,
        status_id=status_id,
        mode_id=mode_id,
        carrier_id=carrier_id,
        pol_port_id=None,
        pod_port_id=None,
        master_bill_lading=None,
        estimated_departure=None,
        estimated_arrival=None,
        created_by=user_email,
        last_changed_by=user_email,
        items=items,
    )

    created_shipment = LogisticsService.create_shipment_with_validation(
        db=db,
        shipment_in=shipment_in,
        user_email=user_email,
    )
    flow_info(
        logger,
        "shipment_finalize_created user=%s shipment_id=%s item_count=%s carrier_id=%s",
        user_email,
        created_shipment.id,
        len(items),
        carrier_id,
        category="shipment",
    )
    DecisionOrchestrator.trigger_evaluation(
        db=db,
        object_id=created_shipment.id,
        object_type="SHIPMENT",
        table_slug="shipment",
        user_email=user_email,
        raise_on_error=False,
    )
    return created_shipment

@router.get("/", response_model=List[ShipmentHeaderSummary])
def list_shipments(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
):
    user_email = _get_user_email(request)
    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.list",
        http_method="GET",
        endpoint_path="/api/v1/shipments",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)

    query = db.query(ShipmentHeaderModel)
    if scope_by_field:
        shipment_ids = _shipment_ids_in_scope(db, scope_by_field)
        if not shipment_ids:
            return []
        query = query.filter(ShipmentHeaderModel.id.in_(sorted(shipment_ids)))

    rows = query.order_by(ShipmentHeaderModel.id.desc()).offset(skip).limit(limit).all()
    return rows

@router.get("/workspace/{shipment_id}", response_model=ShipmentWorkspaceResponse)
def read_shipment_workspace(
    shipment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.workspace",
        http_method="GET",
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    if not _shipment_is_in_scope(db, shipment_id, scope_by_field):
        raise HTTPException(status_code=403, detail="Shipment is outside user scope")

    shipment = (
        db.query(ShipmentHeaderModel)
        .filter(ShipmentHeaderModel.id == shipment_id)
        .first()
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    ship_type = db.query(ShipTypeLookup).filter(ShipTypeLookup.id == shipment.type_id).first()
    ship_status = (
        db.query(ShipmentStatusLookup)
        .filter(ShipmentStatusLookup.id == shipment.status_id)
        .first()
    )
    mode = db.query(TransportModeLookup).filter(TransportModeLookup.id == shipment.mode_id).first()

    carrier_code = None
    carrier_name = None
    if shipment.carrier is not None:
        carrier_code = shipment.carrier.partner_identifier
        carrier_name = shipment.carrier.trade_name or shipment.carrier.legal_name

    pol_port = None
    if shipment.pol_port is not None:
        pol_port = f"{shipment.pol_port.port_code} | {shipment.pol_port.port_name}"

    pod_port = None
    if shipment.pod_port is not None:
        pod_port = f"{shipment.pod_port.port_code} | {shipment.pod_port.port_name}"

    header = ShipmentWorkspaceHeader(
        id=shipment.id,
        shipment_number=shipment.shipment_number,
        external_reference=shipment.external_reference,
        shipment_type=ship_type.type_name if ship_type else None,
        shipment_status=ship_status.status_name if ship_status else None,
        transport_mode=mode.mode_name if mode else None,
        carrier_code=carrier_code,
        carrier_name=carrier_name,
        pol_port=pol_port,
        pod_port=pod_port,
        master_bill_lading=shipment.master_bill_lading,
        estimated_departure=shipment.estimated_departure,
        estimated_arrival=shipment.estimated_arrival,
        actual_arrival=shipment.actual_arrival,
        created_by=shipment.created_by,
        last_changed_by=shipment.last_changed_by,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
    )

    VendorPartner = aliased(PartnerMaster, name="workspace_vendor_partner")
    ForwarderPartner = aliased(PartnerMaster, name="workspace_forwarder_partner")

    item_rows = (
        db.query(
            ShipmentItemModel,
            POScheduleLine.schedule_number.label("schedule_line_no"),
            ProductMaster.sku_identifier.label("sku"),
            ProductMaster.short_description.label("product_description"),
            VendorPartner.legal_name.label("vendor_name"),
            ForwarderPartner.trade_name.label("forwarder_name"),
        )
        .outerjoin(POScheduleLine, POScheduleLine.id == ShipmentItemModel.po_schedule_line_id)
        .outerjoin(PurchaseOrderItem, PurchaseOrderItem.id == ShipmentItemModel.po_item_id)
        .outerjoin(PurchaseOrderHeader, PurchaseOrderHeader.id == PurchaseOrderItem.po_header_id)
        .outerjoin(ProductMaster, ProductMaster.id == PurchaseOrderItem.product_id)
        .outerjoin(VendorPartner, VendorPartner.id == PurchaseOrderHeader.vendor_id)
        .outerjoin(ForwarderPartner, ForwarderPartner.id == PurchaseOrderHeader.forwarder_id)
        .filter(ShipmentItemModel.shipment_header_id == shipment_id)
        .order_by(ShipmentItemModel.shipment_item_number.asc(), ShipmentItemModel.id.asc())
        .all()
    )

    items: list[ShipmentWorkspaceItem] = []
    for (
        si,
        schedule_line_no,
        sku,
        product_description,
        vendor_name,
        forwarder_name,
    ) in item_rows:
        items.append(
            ShipmentWorkspaceItem(
                shipment_item_id=si.id,
                shipment_item_number=si.shipment_item_number,
                po_number=si.po_number,
                predecessor_doc=si.predecessor_doc,
                predecessor_item_no=si.predecessor_item_no,
                schedule_line_no=schedule_line_no,
                shipped_qty=si.shipped_qty,
                package_id=si.package_id,
                gross_weight=si.gross_weight,
                sku=sku,
                product_description=product_description,
                vendor_name=vendor_name,
                forwarder_name=forwarder_name,
            )
        )

    milestone_rows = (
        db.query(ShipmentMilestone, MilestoneTypeLookup)
        .outerjoin(
            MilestoneTypeLookup,
            MilestoneTypeLookup.id == ShipmentMilestone.milestone_id,
        )
        .filter(ShipmentMilestone.shipment_header_id == shipment_id)
        .order_by(ShipmentMilestone.event_datetime.asc(), ShipmentMilestone.id.asc())
        .all()
    )
    milestones = [
        ShipmentWorkspaceMilestone(
            id=ms.id,
            milestone_code=mlt.milestone_code if mlt else None,
            milestone_name=mlt.milestone_name if mlt else None,
            event_datetime=ms.event_datetime,
            location=ms.location,
            notes=ms.notes,
        )
        for (ms, mlt) in milestone_rows
    ]

    doc_rows = (
        db.query(DocumentAttachment, DocumentTypeLookup)
        .outerjoin(DocumentTypeLookup, DocumentTypeLookup.id == DocumentAttachment.type_id)
        .filter(DocumentAttachment.shipment_id == shipment_id)
        .order_by(DocumentAttachment.uploaded_at.desc(), DocumentAttachment.id.desc())
        .all()
    )
    documents = [
        ShipmentWorkspaceDocument(
            id=doc.id,
            document_type=doc_type.doc_name if doc_type else None,
            file_name=doc.file_name,
            file_extension=doc.file_extension,
            file_size_kb=doc.file_size_kb,
            uploaded_at=doc.uploaded_at,
            uploaded_by_id=doc.uploaded_by_id,
        )
        for (doc, doc_type) in doc_rows
    ]

    container_rows = (
        db.query(ShipmentContainer, ContainerTypeLookup)
        .outerjoin(ContainerTypeLookup, ContainerTypeLookup.id == ShipmentContainer.container_type_id)
        .filter(ShipmentContainer.shipment_header_id == shipment_id)
        .order_by(ShipmentContainer.id.asc())
        .all()
    )
    containers = [
        ShipmentWorkspaceContainer(
            id=container.id,
            container_code=ctype.container_code if ctype else None,
            container_name=ctype.container_name if ctype else None,
            container_number=container.container_number,
            seal_number=container.seal_number,
        )
        for (container, ctype) in container_rows
    ]

    texts: list[ShipmentWorkspaceText] = []
    if settings.TEXT_PROFILE_ENABLED:
        runtime_rows = TextProfileService.list_shipment_runtime_texts(db, shipment_id)
        for runtime_row in runtime_rows:
            tt = runtime_row.text_type
            texts.append(
                ShipmentWorkspaceText(
                    id=runtime_row.id,
                    source="shipment_text",
                    text_type_id=runtime_row.text_type_id,
                    text_type_code=tt.text_type_code if tt else None,
                    text_type=tt.text_type_name if tt else None,
                    language=runtime_row.language,
                    text_value=runtime_row.text_value,
                    is_editable=True,
                    is_mandatory=False,
                    is_user_edited=bool(runtime_row.is_user_edited),
                    profile_id=runtime_row.profile_id,
                    profile_version=runtime_row.profile_version,
                )
            )

    if not texts and (not settings.TEXT_PROFILE_ENABLED or settings.TEXT_PROFILE_LEGACY_WORKSPACE_FALLBACK):
        text_rows = (
            db.query(TextMaster, TextTypeLookup)
            .outerjoin(TextTypeLookup, TextTypeLookup.id == TextMaster.type_id)
            .filter(TextMaster.shipment_id == shipment_id)
            .order_by(TextMaster.created_at.desc(), TextMaster.id.desc())
            .all()
        )
        texts.extend(
            [
                ShipmentWorkspaceText(
                    id=text.id,
                    source="text_master",
                    text_type_id=text.type_id,
                    text_type_code=tt.text_type_code if tt else None,
                    text_type=tt.text_type_name if tt else None,
                    language=None,
                    text_value=text.content,
                )
                for (text, tt) in text_rows
            ]
        )

        scoped_rows = (
            db.query(DocText, TextVal, TextTypeLookup)
            .join(TextVal, TextVal.doc_text_id == DocText.id)
            .outerjoin(TextTypeLookup, TextTypeLookup.id == DocText.text_type_id)
            .filter(
                DocText.scope_kind == "SHIPMENT",
                DocText.ship_type_id == shipment.type_id,
                DocText.is_active.is_(True),
                TextVal.is_active.is_(True),
                or_(DocText.partner_id.is_(None), DocText.partner_id == shipment.carrier_id),
            )
            .order_by(TextVal.id.desc())
            .all()
        )
        for doc_text, text_val, tt in scoped_rows:
            texts.append(
                ShipmentWorkspaceText(
                    id=text_val.id,
                    source="text_val",
                    text_type_id=doc_text.text_type_id,
                    text_type_code=tt.text_type_code if tt else None,
                    text_type=tt.text_type_name if tt else None,
                    language=text_val.language,
                    text_value=text_val.text_value,
                )
            )

    return ShipmentWorkspaceResponse(
        header=header,
        items=items,
        milestones=milestones,
        documents=documents,
        containers=containers,
        texts=texts,
    )


@router.put(
    "/{shipment_id}/texts",
    response_model=RuntimeTextsUpdateResponse,
    summary="Update persisted runtime shipment texts",
)
def update_shipment_texts(
    shipment_id: int,
    payload: RuntimeTextsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    if not settings.TEXT_PROFILE_ENABLED:
        raise HTTPException(status_code=400, detail="Text profile framework is disabled.")

    shipment = (
        db.query(ShipmentHeaderModel)
        .filter(ShipmentHeaderModel.id == shipment_id)
        .first()
    )
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.texts.update",
        http_method="PUT",
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    if not _shipment_is_in_scope(db, shipment_id, scope_by_field):
        raise HTTPException(status_code=403, detail="Shipment is outside user scope")

    lock_service = DocumentLockService(db)
    lock_token = request.headers.get(LOCK_TOKEN_HEADER)
    try:
        lock_service.validate_for_write(
            object_type="SHIPMENT",
            document_id=shipment_id,
            owner_email=user_email,
            lock_token=lock_token,
        )
    except DocumentLockFailure as exc:
        raise HTTPException(status_code=409, detail=exc.to_detail())

    rows = TextProfileService.upsert_shipment_runtime_texts(
        db,
        shipment_id=shipment_id,
        rows=[row.model_dump() for row in payload.texts],
        user_email=user_email,
        profile_id=payload.profile_id,
        profile_version=payload.profile_version,
        mark_user_edited=True,
    )
    db.commit()
    return RuntimeTextsUpdateResponse(
        profile_id=payload.profile_id,
        profile_version=payload.profile_version,
        texts=[_runtime_text_to_out(row) for row in rows],
    )

@router.get("/{shipment_id}", 
            response_model=ShipmentHeaderSchema)
def read_shipment(
    shipment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.read",
        http_method="GET",
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    if not _shipment_is_in_scope(db, shipment_id, scope_by_field):
        raise HTTPException(status_code=403, detail="Shipment is outside user scope")

    shipment = LogisticsService.get_shipment_by_id(db=db, shipment_id=shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )
    return shipment

@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipment(
    shipment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.delete",
        http_method="DELETE",
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    if not _shipment_is_in_scope(db, shipment_id, scope_by_field):
        raise HTTPException(status_code=403, detail="Shipment is outside user scope")

    shipment = db.query(ShipmentHeaderModel).filter(ShipmentHeaderModel.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Unlink schedule lines so grouping can see them again
    db.query(POScheduleLine).filter(
        POScheduleLine.shipment_header_id == shipment_id
    ).update({POScheduleLine.shipment_header_id: None})

    db.delete(shipment)
    db.commit()
    return
