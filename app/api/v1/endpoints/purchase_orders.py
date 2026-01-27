from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.purchase_order import POHeaderCreate, POHeader, POInitializationResponse
from app.services.purchase_order_service import PurchaseOrderService
from app.models.po_lookups import (
    PurchaseOrderTypeLookup,
    PurchaseOrderStatusLookup,
    PurchaseOrgLookup,
)
from app.models.company_master import CompanyMaster
from app.models.partner_master import PartnerMaster

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
    companies = db.query(CompanyMaster).all()
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
            {"id": r.id, "code": r.company_code, "name": r.legal_name} for r in companies
        ],
        "vendors": [
            {"id": r.id, "code": r.partner_identifier, "name": r.legal_name} for r in vendors
        ],
    }

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
