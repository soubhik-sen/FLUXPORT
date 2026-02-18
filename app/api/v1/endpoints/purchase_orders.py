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
from app.schemas.text_profile import (
    POTextProfileResolveRequest,
    RuntimeTextsUpdateRequest,
    RuntimeTextsUpdateResponse,
    RuntimeTextRowOut,
    TextProfileResolveResponse,
)
from app.services.purchase_order_service import PurchaseOrderService
from app.services.decision_orchestrator import DecisionOrchestrator
from app.services.authorization_service import user_has_any_permission
from app.services.role_scope_policy import (
    is_scope_denied,
    resolve_scope_by_field,
    scope_deny_detail,
    sanitize_scope_by_field,
)
from app.core.config import settings
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
from app.api.deps.request_identity import get_request_email
from app.services.text_profile_service import TextProfileService
from app.services.document_lock_service import (
    DocumentLockFailure,
    DocumentLockService,
    LOCK_TOKEN_HEADER,
)
router = APIRouter()

def _get_user_email(request: Request) -> str:
    return get_request_email(request)


def _resolve_po_scope_by_field(
    db: Session,
    user_email: str | None,
    *,
    endpoint_key: str = "purchase_orders",
    http_method: str = "GET",
    endpoint_path: str = "/api/v1/purchase-orders",
) -> dict[str, set[int]]:
    return resolve_scope_by_field(
        db,
        user_email=user_email,
        endpoint_key=endpoint_key,
        http_method=http_method,
        endpoint_path=endpoint_path,
    )


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


def _is_po_in_scope(
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


def _po_create_permission_action_keys() -> list[str]:
    return [
        token.strip()
        for token in (settings.PO_CREATE_PERMISSION_ACTION_KEYS or "").split(",")
        if token.strip()
    ]


def _po_create_permission_object_types() -> list[str]:
    return [
        token.strip()
        for token in (settings.PO_CREATE_PERMISSION_OBJECT_TYPES or "").split(",")
        if token.strip()
    ]


def _has_po_create_permission(db: Session, user_email: str | None) -> bool:
    return user_has_any_permission(
        db,
        user_email=user_email,
        action_keys=_po_create_permission_action_keys(),
        object_types=_po_create_permission_object_types(),
    )


def _is_po_create_in_scope(
    po_in: POHeaderCreate,
    scope_by_field: dict[str, set[int]],
    *,
    resolved_company_id: int | None = None,
) -> bool:
    if not scope_by_field:
        return True

    relevant_scope = {
        key: ids
        for key, ids in scope_by_field.items()
        if key in {"customer_id", "company_id", "forwarder_id"} and ids
    }
    # For PO create we enforce customer + forwarder scope dimensions.
    if not relevant_scope:
        return False

    customer_ids = relevant_scope.get("customer_id")
    if customer_ids is not None and po_in.customer_id not in customer_ids:
        return False

    company_ids = relevant_scope.get("company_id")
    if company_ids is not None:
        candidate_company_id = resolved_company_id or po_in.company_id
        if candidate_company_id is None or candidate_company_id not in company_ids:
            return False

    forwarder_ids = relevant_scope.get("forwarder_id")
    if forwarder_ids is not None:
        if po_in.forwarder_id is None or po_in.forwarder_id not in forwarder_ids:
            return False

    return True


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
    if not _has_po_create_permission(db, user_email):
        raise HTTPException(
            status_code=403,
            detail="Missing permission for PO create (requires POCREATE).",
        )

    raw_scope = _resolve_po_scope_by_field(
        db,
        user_email,
        endpoint_key="purchase_orders.create",
        http_method="POST",
        endpoint_path="/api/v1/purchase-orders",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    requested_company_id = (
        db.query(CustomerMaster.company_id)
        .filter(CustomerMaster.id == po_in.customer_id)
        .scalar()
    )
    if not _is_po_create_in_scope(
        po_in,
        scope_by_field,
        resolved_company_id=(
            int(requested_company_id) if requested_company_id is not None else None
        ),
    ):
        raise HTTPException(status_code=403, detail="PO create payload is outside user scope")

    po_in = po_in.model_copy(update={"created_by": user_email, "last_changed_by": user_email})
    created_po = PurchaseOrderService.create_purchase_order(db=db, po_in=po_in, user_email=user_email)
    if settings.TEXT_PROFILE_ENABLED and po_in.texts:
        TextProfileService.upsert_po_runtime_texts(
            db,
            po_id=int(created_po.id),
            rows=[row.model_dump() for row in po_in.texts],
            user_email=user_email,
            profile_id=po_in.text_profile_id,
            profile_version=po_in.text_profile_version,
            mark_user_edited=False,
        )
        db.commit()
    # Post-save hook: trigger decision evaluation for the PO.
    DecisionOrchestrator.trigger_evaluation(
        db=db,
        object_id=created_po.id,
        object_type="PURCHASE_ORDER",
        table_slug="purchase_order",
        user_email=user_email,
        raise_on_error=False,
    )
    return created_po


@router.get(
    "/initialization-data",
    response_model=POInitializationResponse,
    summary="Get initialization data for Create PO",
)
def get_po_initialization_data(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Aggregates lookup data required by the Create PO screen.
    Applies policy scope to customer/vendor options.
    """
    raw_scope = _resolve_po_scope_by_field(
        db,
        _get_user_email(request),
        endpoint_key="purchase_orders.initialization_data",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders/initialization-data",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)

    po_types = db.query(PurchaseOrderTypeLookup).all()
    statuses = db.query(PurchaseOrderStatusLookup).all()
    purchase_orgs = db.query(PurchaseOrgLookup).all()
    customers_query = db.query(CustomerMaster)
    vendors_query = db.query(PartnerMaster)

    if scope_by_field:
        customer_ids = scope_by_field.get("customer_id") or set()
        explicit_company_ids = scope_by_field.get("company_id") or set()
        vendor_ids = scope_by_field.get("vendor_id") or set()
        if customer_ids:
            customers_query = customers_query.filter(
                CustomerMaster.id.in_(sorted(customer_ids))
            )
        elif explicit_company_ids:
            customers_query = customers_query.filter(
                CustomerMaster.company_id.in_(sorted(explicit_company_ids))
            )
        else:
            customers_query = customers_query.filter(CustomerMaster.id == -1)
        if vendor_ids:
            vendors_query = vendors_query.filter(
                PartnerMaster.id.in_(sorted(vendor_ids))
            )
        else:
            vendors_query = vendors_query.filter(PartnerMaster.id == -1)

    customers = customers_query.order_by(CustomerMaster.legal_name.asc()).all()
    vendors = vendors_query.all()
    company_ids = sorted(
        {
            int(customer.company_id)
            for customer in customers
            if customer.company_id is not None
        }
    )
    company_name_by_id: dict[int, str] = {}
    if company_ids:
        company_rows = (
            db.query(CompanyMaster.id, CompanyMaster.legal_name)
            .filter(CompanyMaster.id.in_(company_ids))
            .all()
        )
        company_name_by_id = {
            int(company_id): legal_name
            for company_id, legal_name in company_rows
            if company_id is not None
        }

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
        "customers": [
            {
                "id": r.id,
                "code": r.customer_identifier,
                "name": r.legal_name,
                "company_id": r.company_id,
                "company_name": (
                    company_name_by_id.get(int(r.company_id))
                    if r.company_id is not None
                    else None
                ),
            }
            for r in customers
        ],
        # Backward-compatible key consumed by older clients.
        "companies": [
            {"id": r.id, "code": r.customer_identifier, "name": r.legal_name}
            for r in customers
        ],
        "vendors": [
            {"id": r.id, "code": r.partner_identifier, "name": r.legal_name} for r in vendors
        ],
    }


@router.post(
    "/text-profile/resolve",
    response_model=TextProfileResolveResponse,
    summary="Resolve initial PO text profile and text values",
)
def resolve_po_text_profile(
    payload: POTextProfileResolveRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    if not settings.TEXT_PROFILE_ENABLED:
        return TextProfileResolveResponse(source="disabled", texts=[])

    if not _has_po_create_permission(db, user_email):
        raise HTTPException(
            status_code=403,
            detail="Missing permission for PO create text resolve (requires POCREATE).",
        )

    raw_scope = _resolve_po_scope_by_field(
        db,
        user_email,
        endpoint_key="purchase_orders.text_profile.resolve",
        http_method="POST",
        endpoint_path="/api/v1/purchase-orders/text-profile/resolve",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    resolved_company_id: int | None = payload.company_id
    if payload.customer_id is not None:
        customer = (
            db.query(CustomerMaster)
            .filter(CustomerMaster.id == payload.customer_id)
            .first()
        )
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

    resolved = TextProfileService.resolve_po_text_profile(
        db,
        user_email=user_email,
        context={
            "type_id": payload.type_id,
            "customer_id": payload.customer_id,
            "company_id": resolved_company_id,
            "vendor_id": payload.vendor_id,
            "forwarder_id": payload.forwarder_id,
            "order_date": payload.order_date.isoformat() if payload.order_date else None,
            "currency": payload.currency,
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


@router.get(
    "/workspace/{po_id}",
    response_model=POWorkspaceResponse,
    summary="Get PO workspace view",
)
def read_po_workspace(
    po_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    header_row = (
        db.query(
            PurchaseOrderHeader,
            PurchaseOrderTypeLookup.type_name.label("po_type"),
            PurchaseOrderStatusLookup.status_name.label("po_status"),
            PurchaseOrgLookup.org_name.label("purchase_org"),
            CustomerMaster.legal_name.label("customer_name"),
            CompanyMaster.legal_name.label("company_name"),
            PartnerMaster.legal_name.label("vendor_name"),
        )
        .outerjoin(PurchaseOrderTypeLookup, PurchaseOrderTypeLookup.id == PurchaseOrderHeader.type_id)
        .outerjoin(PurchaseOrderStatusLookup, PurchaseOrderStatusLookup.id == PurchaseOrderHeader.status_id)
        .outerjoin(PurchaseOrgLookup, PurchaseOrgLookup.id == PurchaseOrderHeader.purchase_org_id)
        .outerjoin(CustomerMaster, CustomerMaster.id == PurchaseOrderHeader.customer_id)
        .outerjoin(CompanyMaster, CompanyMaster.id == PurchaseOrderHeader.company_id)
        .outerjoin(PartnerMaster, PartnerMaster.id == PurchaseOrderHeader.vendor_id)
        .filter(PurchaseOrderHeader.id == po_id)
        .first()
    )
    if not header_row:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    header_obj, po_type, po_status, purchase_org, customer_name, company_name, vendor_name = header_row
    raw_scope = _resolve_po_scope_by_field(db, _get_user_email(request))
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)
    if not _is_po_in_scope(
        header_obj,
        scope_by_field,
        legacy_customer_company_ids=legacy_customer_company_ids,
    ):
        raise HTTPException(status_code=403, detail="Purchase Order is outside user scope")

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
        customer_id=header_obj.customer_id,
        customer_name=customer_name,
        company_id=header_obj.company_id,
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

    texts: list[POWorkspaceText] = []
    if settings.TEXT_PROFILE_ENABLED:
        runtime_rows = TextProfileService.list_po_runtime_texts(db, po_id)
        for runtime_row in runtime_rows:
            tt = runtime_row.text_type
            texts.append(
                POWorkspaceText(
                    id=runtime_row.id,
                    source="po_text",
                    text_type_id=runtime_row.text_type_id,
                    text_type_code=tt.text_type_code if tt else None,
                    text_type=tt.text_type_name if tt else None,
                    language=runtime_row.language,
                    text_value=runtime_row.text_value,
                    valid_from=None,
                    valid_to=None,
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
            .filter(TextMaster.po_header_id == po_id)
            .order_by(TextMaster.created_at.desc(), TextMaster.id.desc())
            .all()
        )
        texts.extend(
            [
                POWorkspaceText(
                    id=text.id,
                    source="text_master",
                    text_type_id=text.type_id,
                    text_type_code=tt.text_type_code if tt else None,
                    text_type=tt.text_type_name if tt else None,
                    language=None,
                    text_value=text.content,
                    valid_from=None,
                    valid_to=None,
                )
                for (text, tt) in text_rows
            ]
        )

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
                    text_type_id=doc_text.text_type_id,
                    text_type_code=tt.text_type_code if tt else None,
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


@router.put(
    "/{po_id}/texts",
    response_model=RuntimeTextsUpdateResponse,
    summary="Update persisted runtime PO texts",
)
def update_po_texts(
    po_id: int,
    payload: RuntimeTextsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    if not settings.TEXT_PROFILE_ENABLED:
        raise HTTPException(status_code=400, detail="Text profile framework is disabled.")

    header = db.query(PurchaseOrderHeader).filter(PurchaseOrderHeader.id == po_id).first()
    if header is None:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    raw_scope = _resolve_po_scope_by_field(
        db,
        user_email,
        endpoint_key="purchase_orders.texts.update",
        http_method="PUT",
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)
    if not _is_po_in_scope(
        header,
        scope_by_field,
        legacy_customer_company_ids=legacy_customer_company_ids,
    ):
        raise HTTPException(status_code=403, detail="Purchase Order is outside user scope")

    lock_service = DocumentLockService(db)
    lock_token = request.headers.get(LOCK_TOKEN_HEADER)
    try:
        lock_service.validate_for_write(
            object_type="PURCHASE_ORDER",
            document_id=po_id,
            owner_email=user_email,
            lock_token=lock_token,
        )
    except DocumentLockFailure as exc:
        raise HTTPException(status_code=409, detail=exc.to_detail())

    rows = TextProfileService.upsert_po_runtime_texts(
        db,
        po_id=po_id,
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

@router.get("/{po_id}", 
            response_model=POHeader,
            summary="Get PO Details")
def read_po(
    po_id: int,
    request: Request,
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
    raw_scope = _resolve_po_scope_by_field(db, _get_user_email(request))
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)
    if not _is_po_in_scope(
        po,
        scope_by_field,
        legacy_customer_company_ids=legacy_customer_company_ids,
    ):
        raise HTTPException(status_code=403, detail="Purchase Order is outside user scope")
    return po

@router.get("/", 
            response_model=List[POHeader],
            summary="List Purchase Orders")
def list_pos(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    vendor_id: int = None
):
    """
    Returns a paginated list of POs. 
    Includes optional filters which are standard for ERP grid views.
    """
    raw_scope = _resolve_po_scope_by_field(db, _get_user_email(request))
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)
    return PurchaseOrderService.get_multi_pos(
        db=db,
        skip=skip,
        limit=limit,
        vendor_id=vendor_id,
        scope_by_field=scope_by_field,
        legacy_customer_company_ids=legacy_customer_company_ids,
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

    raw_scope = _resolve_po_scope_by_field(
        db,
        _get_user_email(request),
        endpoint_key="purchase_orders.schedule_lines_merge",
        http_method="POST",
        endpoint_path="/api/v1/purchase-orders/schedule-lines/merge",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    legacy_customer_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)

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

    if scope_by_field:
        forbidden_ids: list[int] = []
        for line in lines:
            header = line.item.header if line.item is not None else None
            if header is None:
                forbidden_ids.append(line.id)
                continue
            in_scope = _is_po_in_scope(
                header,
                scope_by_field,
                legacy_customer_company_ids=legacy_customer_company_ids,
            )
            if not in_scope:
                forbidden_ids.append(line.id)
        if forbidden_ids:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Selected schedule lines are outside user scope.",
                    "scope_keys": sorted(scope_by_field.keys()),
                    "forbidden_schedule_line_ids": sorted(forbidden_ids),
                },
            )

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
