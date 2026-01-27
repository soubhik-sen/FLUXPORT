from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.partner_master import (
    DuplicateError,
    create_partner_master,
    delete_partner_master,
    get_partner_master,
    list_partner_master,
    update_partner_master,
)
from app.db.session import get_db
from app.schemas.partner_master import PartnerMasterCreate, PartnerMasterOut, PartnerMasterUpdate

router = APIRouter(prefix="/partner-master", tags=["partner-master"])


@router.post("", response_model=PartnerMasterOut, status_code=status.HTTP_201_CREATED)
def create_partner_master_api(payload: PartnerMasterCreate, db: Session = Depends(get_db)):
    try:
        return create_partner_master(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{partner_id}", response_model=PartnerMasterOut)
def get_partner_master_api(partner_id: int, db: Session = Depends(get_db)):
    obj = get_partner_master(db, partner_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Partner not found")
    return obj


@router.get("", response_model=list[PartnerMasterOut])
def list_partner_master_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_active: bool | None = Query(None),
    role_id: int | None = Query(None),
    q: str | None = Query(None, description="Search by identifier/legal/trade name"),
    db: Session = Depends(get_db),
):
    return list_partner_master(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        role_id=role_id,
        q=q,
    )


@router.patch("/{partner_id}", response_model=PartnerMasterOut)
def update_partner_master_api(partner_id: int, payload: PartnerMasterUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_partner_master(db, partner_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Partner not found")
    return obj


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner_master_api(
    partner_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_partner_master(db, partner_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Partner not found")
    return None
