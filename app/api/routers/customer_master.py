from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps.request_identity import get_request_email
from app.crud.customer_master import (
    DuplicateError,
    create_customer_master,
    delete_customer_master,
    get_customer_master,
    list_customer_master,
    update_customer_master,
)
from app.db.session import get_db
from app.schemas.customer_master import CustomerMasterCreate, CustomerMasterOut, CustomerMasterUpdate

router = APIRouter(prefix="/customer-master", tags=["customer-master"])


def _get_user_email(request: Request) -> str:
    return get_request_email(request)


@router.post("", response_model=CustomerMasterOut, status_code=status.HTTP_201_CREATED)
def create_customer_master_api(
    payload: CustomerMasterCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        return create_customer_master(db, payload, current_user_email=_get_user_email(request))
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{customer_id}", response_model=CustomerMasterOut)
def get_customer_master_api(customer_id: int, db: Session = Depends(get_db)):
    obj = get_customer_master(db, customer_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


@router.get("", response_model=list[CustomerMasterOut])
def list_customer_master_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_active: bool | None = Query(None),
    role_id: int | None = Query(None),
    q: str | None = Query(None, description="Search by identifier/legal/trade name"),
    db: Session = Depends(get_db),
):
    return list_customer_master(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        role_id=role_id,
        q=q,
    )


@router.patch("/{customer_id}", response_model=CustomerMasterOut)
def update_customer_master_api(
    customer_id: int,
    payload: CustomerMasterUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        obj = update_customer_master(db, customer_id, payload, current_user_email=_get_user_email(request))
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_master_api(
    customer_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_customer_master(db, customer_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Customer not found")
    return None
