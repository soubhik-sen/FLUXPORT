from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.partner_type import (
    DuplicateError,
    create_partner_type,
    delete_partner_type,
    get_partner_type,
    list_partner_types,
    update_partner_type,
)
from app.db.session import get_db
from app.schemas.partner_type import PartnerTypeCreate, PartnerTypeOut, PartnerTypeUpdate

router = APIRouter(prefix="/partner-type", tags=["partner-type"])


@router.post("", response_model=PartnerTypeOut, status_code=status.HTTP_201_CREATED)
def create_partner_type_api(payload: PartnerTypeCreate, db: Session = Depends(get_db)):
    try:
        return create_partner_type(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{type_id}", response_model=PartnerTypeOut)
def get_partner_type_api(type_id: int, db: Session = Depends(get_db)):
    obj = get_partner_type(db, type_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Partner type not found")
    return obj


@router.get("", response_model=list[PartnerTypeOut])
def list_partner_types_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_partner_types(db, skip=skip, limit=limit, is_active=is_active)


@router.patch("/{type_id}", response_model=PartnerTypeOut)
def update_partner_type_api(type_id: int, payload: PartnerTypeUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_partner_type(db, type_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Partner type not found")
    return obj


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner_type_api(
    type_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_partner_type(db, type_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Partner type not found")
    return None
