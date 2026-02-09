from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import or_

from app.db.session import get_db
from app.schemas.purchase_order import (
    POHeaderCreate,
    POHeader,
    POInitializationResponse,
    POScheduleMergeRequest,
    POWorkspaceResponse,
    POWorkspaceHeader,
    POWorkspaceItem,
    POWorkspaceSchedule,
    POWorkspaceText,
    POWorkspaceDocument,
    POWorkspaceCharge,
)
from app.services.purchase_order_service import PurchaseOrderService
from app.models.po_schedule_line import POScheduleLine
from app.models.shipment import ShipmentItem
from app.models.shipment import ShipmentHeader
from app.models.po_lookups import (
    PurchaseOrderTypeLookup,
    PurchaseOrderStatusLookup,
    PurchaseOrgLookup,
    PurchaseOrderItemStatusLookup,
)
from app.models.customer_master import CustomerMaster
from app.models.partner_master import PartnerMaster
from app.models.company_master import CompanyMaster
from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.models.product_master import ProductMaster
from app.models.product_lookups import UomLookup
from app.models.document import DocumentAttachment
from app.models.doc_lookups import DocumentTypeLookup
from app.models.text_master import TextMaster
from app.models.text_lookups import TextTypeLookup
from app.models.doc_text import DocText, TextVal

router = APIRouter()

def _get_user_email(request: Request) -> str:
    return request.headers.get("X-User-Email") or request.headers.get("X-User") or "system@local"

@router.post("/", 
             response_model=POHeader, 
             status_code=status.HTTP_201_CREATED,
             summary="Create a new Purchase Order",
             description="Creates a PO Header and associated items. Recalculates totals and validates vendor status.")
def create_po(
    *,
    db: Session = Depends(get_db),
    request: Request,
    po_in: POHeaderCreate
):
    """
    Enterprise Entry Point for PO Creation.
    Delegates validation and persistence to the PurchaseOrderService.
    """
    user_email = _get_user_email(request)
    po_in = po_in.model_copy(update={"created_by": user_email, "last_changed_by": user_email})
    return PurchaseOrderService.create_purchase_order(db=db, po_in=po_in, user_email=user_email)


@router.get(
    "/initialization-data",
    response_model=POInitializationResponse,
    summary="Get initialization data for Create PO",
)
def get_po_initialization_data(db: Session = Depends(get_db)):
    """
    Aggregates lookup data required by the Create PO screen.
    """
    po_types = db.query(PurchaseOrderTypeLookup).all()
    statuses = db.query(PurchaseOrderStatusLookup).all()
    purchase_orgs = db.query(PurchaseOrgLookup).all()
    customers = db.query(CustomerMaster).all()
    vendors = db.query(PartnerMaster).all()

    return {
        "po_types": [
            {"id": r.id, "code": r.type_code, "name": r.type_name} for r in po_types
        ],
        "statuses": [
            {"id": r.id, "code": r.status_code, "name": r.status_name} for r in statuses
        ],
        "purchase_orgs": [
            {"id": r.id, "code": r.org_code, "name": r.org_name} for r in purchase_orgs
        ],
        "companies": [
            {"id": r.id, "code": r.customer_identifier, "name": r.legal_name} for r in customers
        ],
        "vendors": [
            {"id": r.id, "code": r.partner_identifier, "name": r.legal_name} for r in vendors
        ],
    }


@router.get(
    "/workspace/{po_id}",
    response_model=POWorkspaceResponse,
    summary="Get PO workspace view",
)
def read_po_workspace(
    po_id: int,
    db: Session = Depends(get_db),
):
    header_row = (
        db.query(
            PurchaseOrderHeader,
            PurchaseOrderTypeLookup.type_name.label("po_type"),
            PurchaseOrderStatusLookup.status_name.label("po_status"),
            PurchaseOrgLookup.org_name.label("purchase_org"),
            CompanyMaster.legal_name.label("company_name"),
            PartnerMaster.legal_name.label("vendor_name"),
        )
        .outerjoin(PurchaseOrderTypeLookup, PurchaseOrderTypeLookup.id == PurchaseOrderHeader.type_id)
        .outerjoin(PurchaseOrderStatusLookup, PurchaseOrderStatusLookup.id == PurchaseOrderHeader.status_id)
        .outerjoin(PurchaseOrgLookup, PurchaseOrgLookup.id == PurchaseOrderHeader.purchase_org_id)
        .outerjoin(CompanyMaster, CompanyMaster.id == PurchaseOrderHeader.company_id)
        .outerjoin(PartnerMaster, PartnerMaster.id == PurchaseOrderHeader.vendor_id)
        .filter(PurchaseOrderHeader.id == po_id)
        .first()
    )
    if not header_row:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    header_obj, po_type, po_status, purchase_org, company_name, vendor_name = header_row
    forwarder_name = None
    if header_obj.forwarder_id is not None:
        forwarder = db.query(PartnerMaster).filter(PartnerMaster.id == header_obj.forwarder_id).first()
        if forwarder is not None:
            forwarder_name = forwarder.trade_name or forwarder.legal_name

    header = POWorkspaceHeader(
        id=header_obj.id,
        po_number=header_obj.po_number,
        po_type=po_type,
        po_status=po_status,
        purchase_org=purchase_org,
        company_name=company_name,
        vendor_name=vendor_name,
        forwarder_name=forwarder_name,
        order_date=header_obj.order_date,
        currency=header_obj.currency,
        total_amount=header_obj.total_amount,
        created_by=header_obj.created_by,
        last_changed_by=header_obj.last_changed_by,
        created_at=header_obj.created_at,
        updated_at=header_obj.updated_at,
    )

    item_rows = (
        db.query(
            PurchaseOrderItem,
            ProductMaster.sku_identifier.label("sku"),
            ProductMaster.short_description.label("product_description"),
            UomLookup.uom_code.label("uom_code"),
            PurchaseOrderItemStatusLookup.status_name.label("item_status"),
        )
        .outerjoin(ProductMaster, ProductMaster.id == PurchaseOrderItem.product_id)
        .outerjoin(UomLookup, UomLookup.id == ProductMaster.uom_id)
        .outerjoin(PurchaseOrderItemStatusLookup, PurchaseOrderItemStatusLookup.id == PurchaseOrderItem.status_id)
        .filter(PurchaseOrderItem.po_header_id == po_id)
        .order_by(PurchaseOrderItem.item_number.asc(), PurchaseOrderItem.id.asc())
        .all()
    )
    items = [
        POWorkspaceItem(
            po_item_id=item.id,
            item_number=item.item_number,
            product_id=item.product_id,
            sku=sku,
            product_description=product_description,
            uom_code=uom_code,
            item_status=item_status,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
        )
        for (item, sku, product_description, uom_code, item_status) in item_rows
    ]

    schedule_rows = (
        db.query(
            POScheduleLine,
            PurchaseOrderItem.item_number.label("item_number"),
            ShipmentHeader.shipment_number.label("shipment_number"),
        )
        .join(PurchaseOrderItem, PurchaseOrderItem.id == POScheduleLine.po_item_id)
        .outerjoin(ShipmentHeader, ShipmentHeader.id == POScheduleLine.shipment_header_id)
        .filter(PurchaseOrderItem.po_header_id == po_id)
        .order_by(PurchaseOrderItem.item_number.asc(), POScheduleLine.schedule_number.asc(), POScheduleLine.id.asc())
        .all()
    )
    schedules = [
        POWorkspaceSchedule(
            po_schedule_line_id=schedule.id,
            po_item_id=schedule.po_item_id,
            item_number=item_number,
            schedule_number=schedule.schedule_number,
            quantity=schedule.quantity,
            received_qty=schedule.received_qty,
            delivery_date=schedule.delivery_date,
            shipment_header_id=schedule.shipment_header_id,
            shipment_number=shipment_number,
        )
        for (schedule, item_number, shipment_number) in schedule_rows
    ]

    text_rows = (
        db.query(TextMaster, TextTypeLookup)
        .outerjoin(TextTypeLookup, TextTypeLookup.id == TextMaster.type_id)
        .filter(TextMaster.po_header_id == po_id)
        .order_by(TextMaster.created_at.desc(), TextMaster.id.desc())
        .all()
    )
    texts = [
        POWorkspaceText(
            id=text.id,
            source="text_master",
            text_type=tt.text_type_name if tt else None,
            language=None,
            text_value=text.content,
            valid_from=None,
            valid_to=None,
        )
        for (text, tt) in text_rows
    ]

    partner_scope = [header_obj.vendor_id]
    if header_obj.forwarder_id is not None:
        partner_scope.append(header_obj.forwarder_id)

    scoped_rows = (
        db.query(DocText, TextVal, TextTypeLookup)
        .join(TextVal, TextVal.doc_text_id == DocText.id)
        .outerjoin(TextTypeLookup, TextTypeLookup.id == DocText.text_type_id)
        .filter(
            DocText.scope_kind == "PO",
            DocText.po_type_id == header_obj.type_id,
            DocText.is_active.is_(True),
            TextVal.is_active.is_(True),
            or_(DocText.partner_id.is_(None), DocText.partner_id.in_(partner_scope)),
        )
        .order_by(TextVal.id.desc())
        .all()
    )
    for (doc_text, text_val, tt) in scoped_rows:
        texts.append(
            POWorkspaceText(
                id=text_val.id,
                source="text_val",
                text_type=tt.text_type_name if tt else None,
                language=text_val.language,
                text_value=text_val.text_value,
                valid_from=text_val.valid_from,
                valid_to=text_val.valid_to,
            )
        )

    doc_rows = (
        db.query(DocumentAttachment, DocumentTypeLookup)
        .outerjoin(DocumentTypeLookup, DocumentTypeLookup.id == DocumentAttachment.type_id)
        .filter(DocumentAttachment.po_header_id == po_id)
        .order_by(DocumentAttachment.uploaded_at.desc(), DocumentAttachment.id.desc())
        .all()
    )
    documents = [
        POWorkspaceDocument(
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

    charges: list[POWorkspaceCharge] = []
    total_amount = (header_obj.total_amount or Decimal("0.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    line_sum = sum((item.line_total or Decimal("0.00")) for item in (row[0] for row in item_rows))
    line_sum = Decimal(line_sum).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    charges.append(
        POWorkspaceCharge(
            charge_code="MATERIAL_VALUE",
            charge_name="Material Value",
            amount=total_amount,
            currency=header_obj.currency,
            source="derived",
        )
    )
    delta = (total_amount - line_sum).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if delta != Decimal("0.00"):
        charges.append(
            POWorkspaceCharge(
                charge_code="ROUNDING_ADJUSTMENT",
                charge_name="Rounding Adjustment",
                amount=delta,
                currency=header_obj.currency,
                source="derived",
            )
        )

    return POWorkspaceResponse(
        header=header,
        items=items,
        schedules=schedules,
        texts=texts,
        documents=documents,
        charges=charges,
    )

@router.get("/{po_id}", 
            response_model=POHeader,
            summary="Get PO Details")
def read_po(
    po_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves a single PO with items. 
    In an enterprise app, we typically add authorization checks here 
    to ensure the user has access to the specific Purchase Org.
    """
    po = PurchaseOrderService.get_po_by_id(db=db, po_id=po_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase Order not found"
        )
    return po

@router.get("/", 
            response_model=List[POHeader],
            summary="List Purchase Orders")
def list_pos(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    vendor_id: int = None
):
    """
    Returns a paginated list of POs. 
    Includes optional filters which are standard for ERP grid views.
    """
    return PurchaseOrderService.get_multi_pos(
        db=db, skip=skip, limit=limit, vendor_id=vendor_id
    )


@router.post(
    "/schedule-lines/merge",
    status_code=status.HTTP_200_OK,
    summary="Merge PO schedule lines",
)
def merge_schedule_lines(
    *,
    db: Session = Depends(get_db),
    request: Request,
    payload: POScheduleMergeRequest,
):
    merges = payload.merges or []
    if not merges:
        raise HTTPException(status_code=400, detail="No schedule line merges provided.")

    source_ids = [m.source_schedule_line_id for m in merges]
    target_ids = [m.target_schedule_line_id for m in merges]
    all_ids = set(source_ids + target_ids)
    # Lock candidate schedule lines to avoid merge/finalize race conditions.
    lines = (
        db.query(POScheduleLine)
        .filter(POScheduleLine.id.in_(all_ids))
        .with_for_update()
        .all()
    )
    line_map = {line.id: line for line in lines}

    missing = [sid for sid in all_ids if sid not in line_map]
    if missing:
        raise HTTPException(status_code=404, detail={"missing_schedule_line_ids": missing})

    for merge in merges:
        if merge.source_schedule_line_id == merge.target_schedule_line_id:
            raise HTTPException(status_code=400, detail="Source and target schedule line cannot be the same.")

        source = line_map[merge.source_schedule_line_id]
        target = line_map[merge.target_schedule_line_id]
        if source.po_item_id != target.po_item_id:
            raise HTTPException(status_code=400, detail="Schedule lines must belong to the same PO item.")

        # Block merges that touch shipped schedule lines
        if source.shipment_header_id is not None or target.shipment_header_id is not None:
            raise HTTPException(status_code=400, detail="Cannot merge schedule lines already linked to a shipment.")

        # Extra guard: shipment items referencing these lines
        shipped = db.query(ShipmentItem).filter(
            ShipmentItem.po_schedule_line_id.in_([source.id, target.id])
        ).count()
        if shipped > 0:
            raise HTTPException(status_code=400, detail="Cannot merge schedule lines with shipment items.")

        target.quantity = target.quantity + source.quantity
        db.delete(source)

    db.commit()
    return {"merged": len(merges)}
