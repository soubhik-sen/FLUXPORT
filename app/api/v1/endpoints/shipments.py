from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List

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
)
from app.services.logistics_service import LogisticsService
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
from app.models.user_partner_link import UserPartnerLink
from app.models.user_customer_link import UserCustomerLink
from app.models.partner_role import PartnerRole
from app.models.customer_master import CustomerMaster
from app.models.document import DocumentAttachment
from app.models.doc_lookups import DocumentTypeLookup
from sqlalchemy.orm import aliased

router = APIRouter()

def _get_user_email(request: Request) -> str:
    return request.headers.get("X-User-Email") or request.headers.get("X-User") or "system@local"

def _resolve_partner_ids_by_role_codes(db: Session, user_email: str, role_codes: List[str]) -> list[int]:
    rows = (
        db.query(UserPartnerLink.partner_id)
        .join(PartnerMaster, PartnerMaster.id == UserPartnerLink.partner_id)
        .join(PartnerRole, PartnerRole.id == PartnerMaster.role_id)
        .filter(UserPartnerLink.user_email == user_email)
        .filter(UserPartnerLink.deletion_indicator == False)
        .filter(PartnerRole.role_code.in_(role_codes))
        .all()
    )
    return sorted({r[0] for r in rows if r and r[0] is not None})

def _resolve_forwarder_partner_ids(db: Session, user_email: str) -> list[int]:
    return _resolve_partner_ids_by_role_codes(db, user_email, ["FO", "FORWARDER"])

def _resolve_supplier_partner_ids(db: Session, user_email: str) -> list[int]:
    return _resolve_partner_ids_by_role_codes(db, user_email, ["SU", "SUPPLIER"])

def _resolve_customer_ids(db: Session, user_email: str) -> list[int]:
    rows = (
        db.query(UserCustomerLink.customer_id)
        .join(CustomerMaster, CustomerMaster.id == UserCustomerLink.customer_id)
        .filter(UserCustomerLink.user_email == user_email)
        .filter(UserCustomerLink.deletion_indicator == False)
        .filter(CustomerMaster.is_active == True)
        .all()
    )
    return sorted({r[0] for r in rows if r and r[0] is not None})

def _resolve_grouping_scope(db: Session, user_email: str) -> tuple[str | None, set[int]]:
    forwarder_ids = _resolve_forwarder_partner_ids(db, user_email)
    if forwarder_ids:
        return ("forwarder_id", set(forwarder_ids))
    supplier_ids = _resolve_supplier_partner_ids(db, user_email)
    if supplier_ids:
        return ("vendor_id", set(supplier_ids))
    customer_ids = _resolve_customer_ids(db, user_email)
    if customer_ids:
        return ("company_id", set(customer_ids))
    return (None, set())

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
    shipment_in = shipment_in.model_copy(update={"created_by": user_email, "last_changed_by": user_email})
    return LogisticsService.create_shipment_with_validation(
        db=db,
        shipment_in=shipment_in,
        user_email=user_email,
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
            return existing

    def _as_float(value) -> float:
        return float(value)

    schedule_line_ids = payload.schedule_line_ids or []
    lines = payload.lines or []
    if not schedule_line_ids and not lines:
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
        raise HTTPException(status_code=404, detail={"missing_schedule_line_ids": missing})

    # Enforce the same role scope used by grouping report (forwarder > supplier > customer).
    scope_key, scoped_ids = _resolve_grouping_scope(db, user_email)
    if scope_key and scoped_ids:
        forbidden_ids: list[int] = []
        for line in schedule_lines:
            header = line.item.header if line.item is not None else None
            if header is None:
                forbidden_ids.append(line.id)
                continue
            scope_value = getattr(header, scope_key, None)
            if scope_value not in scoped_ids:
                forbidden_ids.append(line.id)
        if forbidden_ids:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Selected schedule lines are outside user scope.",
                    "scope_key": scope_key,
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

    return LogisticsService.create_shipment_with_validation(
        db=db,
        shipment_in=shipment_in,
        user_email=user_email,
    )

@router.get("/", response_model=List[ShipmentHeaderSummary])
def list_shipments(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
):
    rows = (
        db.query(ShipmentHeaderModel)
        .order_by(ShipmentHeaderModel.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rows

@router.get("/workspace/{shipment_id}", response_model=ShipmentWorkspaceResponse)
def read_shipment_workspace(
    shipment_id: int,
    db: Session = Depends(get_db),
):
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

    return ShipmentWorkspaceResponse(
        header=header,
        items=items,
        milestones=milestones,
        documents=documents,
        containers=containers,
    )

@router.get("/{shipment_id}", 
            response_model=ShipmentHeaderSchema)
def read_shipment(
    shipment_id: int,
    db: Session = Depends(get_db)
):
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
    db: Session = Depends(get_db)
):
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
