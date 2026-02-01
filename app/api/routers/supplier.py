from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.supplier import (
    DuplicateError,
    create_supplier,
    delete_supplier,
    get_supplier,
    list_suppliers,
    update_supplier,
)
from app.db.session import get_db
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier_api(payload: SupplierCreate, db: Session = Depends(get_db)):
    try:
        return create_supplier(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=SupplierOut)
def get_supplier_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_supplier(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier mapping not found")
    return obj


@router.get("", response_model=list[SupplierOut])
def list_suppliers_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    include_deleted: bool = Query(False),
    as_of: date | None = Query(None),
    supplier_id: int | None = Query(None, ge=1),
    branch_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    return list_suppliers(
        db,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        as_of=as_of,
        supplier_id=supplier_id,
        branch_id=branch_id,
    )


@router.patch("/{row_id}", response_model=SupplierOut)
def update_supplier_api(row_id: int, payload: SupplierUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_supplier(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Supplier mapping not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier_api(
    row_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_supplier(db, row_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Supplier mapping not found")
    return None
