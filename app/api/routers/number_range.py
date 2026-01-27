from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db  # Assuming your DB session utility
from app.services.number_range_get import NumberRangeService
from app.schemas.number_range import (
    NumberRangeCreate, 
    NumberRangeUpdate, 
    NumberRangeResponse
)

# We use a prefix to group all sequence-related settings
router = APIRouter(
    prefix="/api/v1/sys-number-ranges",
    tags=["System Settings - Number Ranges"]
)

@router.get("", response_model=list[NumberRangeResponse])
def fetch_all_ranges(db: Session = Depends(get_db)):
    """Enterprise view: List all configured sequences for PO, INV, etc."""
    return NumberRangeService.list_ranges(db)


@router.get("/next")
def get_next_number(
    doc_category: str,
    doc_type_id: int,
    db: Session = Depends(get_db),
):
    """
    Generate the next document number for a category/type pair.
    """
    try:
        return {"next_number": NumberRangeService.get_next_number(db, doc_category, doc_type_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("", response_model=NumberRangeResponse, status_code=status.HTTP_201_CREATED)
def create_range_config(payload: NumberRangeCreate, db: Session = Depends(get_db)):
    """Register a new sequence for a Doc Category + Type ID pair."""
    try:
        return NumberRangeService.create_range(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{range_id}", response_model=NumberRangeResponse)
def modify_range_config(range_id: int, payload: NumberRangeUpdate, db: Session = Depends(get_db)):
    """Update prefix or toggle activity without resetting the counter."""
    updated = NumberRangeService.update_range(db, range_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Sequence configuration not found")
    return updated

@router.delete("/{range_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_range_config(range_id: int, db: Session = Depends(get_db)):
    """Delete a sequence configuration."""
    deleted = NumberRangeService.delete_range(db, range_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sequence configuration not found")
    return None

