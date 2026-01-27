from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.customer_type import (
    DuplicateError,
    create_customer_type,
    delete_customer_type,
    get_customer_type,
    list_customer_types,
    update_customer_type,
)
from app.db.session import get_db
from app.schemas.customer_type import CustomerTypeCreate, CustomerTypeOut, CustomerTypeUpdate

router = APIRouter(prefix="/customer-type", tags=["customer-type"])


@router.post("", response_model=CustomerTypeOut, status_code=status.HTTP_201_CREATED)
def create_customer_type_api(payload: CustomerTypeCreate, db: Session = Depends(get_db)):
    try:
        return create_customer_type(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{type_id}", response_model=CustomerTypeOut)
def get_customer_type_api(type_id: int, db: Session = Depends(get_db)):
    obj = get_customer_type(db, type_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer type not found")
    return obj


@router.get("", response_model=list[CustomerTypeOut])
def list_customer_types_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_customer_types(db, skip=skip, limit=limit, is_active=is_active)


@router.patch("/{type_id}", response_model=CustomerTypeOut)
def update_customer_type_api(type_id: int, payload: CustomerTypeUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_customer_type(db, type_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Customer type not found")
    return obj


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_type_api(
    type_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_customer_type(db, type_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Customer type not found")
    return None
