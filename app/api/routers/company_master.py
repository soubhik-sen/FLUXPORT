from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.company_master import (
    DuplicateError,
    create_company_master,
    delete_company_master,
    get_company_master,
    list_company_master,
    update_company_master,
)
from app.db.session import get_db
from app.schemas.company_master import CompanyMasterCreate, CompanyMasterOut, CompanyMasterUpdate

router = APIRouter(prefix="/company-master", tags=["company-master"])


@router.post("", response_model=CompanyMasterOut, status_code=status.HTTP_201_CREATED)
def create_company_master_api(payload: CompanyMasterCreate, db: Session = Depends(get_db)):
    try:
        return create_company_master(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{company_id}", response_model=CompanyMasterOut)
def get_company_master_api(company_id: int, db: Session = Depends(get_db)):
    obj = get_company_master(db, company_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return obj


@router.get("", response_model=list[CompanyMasterOut])
def list_company_master_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    is_active: bool | None = Query(None),
    q: str | None = Query(None, description="Search by company code/branch/legal/trade name"),
    db: Session = Depends(get_db),
):
    return list_company_master(db, skip=skip, limit=limit, is_active=is_active, q=q)


@router.patch("/{company_id}", response_model=CompanyMasterOut)
def update_company_master_api(
    company_id: int,
    payload: CompanyMasterUpdate,
    db: Session = Depends(get_db),
):
    try:
        obj = update_company_master(db, company_id, payload)
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if not obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return obj


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_master_api(
    company_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_company_master(db, company_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Company not found")
    return None
