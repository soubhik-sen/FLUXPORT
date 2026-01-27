from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.shipment import ShipmentHeaderCreate, ShipmentHeader
from app.services.logistics_service import LogisticsService

router = APIRouter()

def _get_user_email(request: Request) -> str:
    return request.headers.get("X-User-Email") or request.headers.get("X-User") or "system@local"

@router.post("/", 
             response_model=ShipmentHeader, 
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

@router.get("/{shipment_id}", 
            response_model=ShipmentHeader)
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
