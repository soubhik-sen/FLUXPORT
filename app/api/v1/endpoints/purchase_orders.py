from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.purchase_order import POHeaderCreate, POHeader
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter()

@router.post("/", 
             response_model=POHeader, 
             status_code=status.HTTP_201_CREATED,
             summary="Create a new Purchase Order",
             description="Creates a PO Header and associated items. Recalculates totals and validates vendor status.")
def create_po(
    *,
    db: Session = Depends(get_db),
    po_in: POHeaderCreate
):
    """
    Enterprise Entry Point for PO Creation.
    Delegates validation and persistence to the PurchaseOrderService.
    """
    return PurchaseOrderService.create_purchase_order(db=db, po_in=po_in)

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