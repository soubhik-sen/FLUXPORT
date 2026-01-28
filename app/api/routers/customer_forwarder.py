from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.crud.customer_forwarder import (
    DuplicateError,
    create_customer_forwarder,
    delete_customer_forwarder,
    delete_customer_forwarder_by_pair,
    get_customer_forwarder,
    get_customer_forwarder_by_pair,
    list_customer_forwarders,
    list_customer_forwarders_with_names,
    search_customers,
    search_forwarders,
    update_customer_forwarder,
)
from app.db.session import get_db
from app.schemas.customer_forwarder import (
    CustomerForwarderCreate,
    CustomerForwarderOut,
    CustomerForwarderUpdate,
    SearchResult,
)

router = APIRouter(prefix="/customer-forwarders", tags=["customer-forwarders"])

def _get_user_email(request: Request) -> str:
    return request.headers.get("X-User-Email") or request.headers.get("X-User") or "system@local"


@router.post("", response_model=CustomerForwarderOut, status_code=status.HTTP_201_CREATED)
def create_customer_forwarder_api(
    payload: CustomerForwarderCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        return create_customer_forwarder(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/link", response_model=CustomerForwarderOut, status_code=status.HTTP_201_CREATED)
def link_customer_forwarder_api(
    payload: CustomerForwarderCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    existing = get_customer_forwarder_by_pair(db, payload.customer_id, payload.forwarder_id)
    if existing:
        return existing
    try:
        return create_customer_forwarder(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=CustomerForwarderOut)
def get_customer_forwarder_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_customer_forwarder(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    return obj


@router.get("", response_model=list[CustomerForwarderOut])
def list_customer_forwarders_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    customer_id: int | None = Query(None, ge=1),
    forwarder_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_customer_forwarders_with_names(
        db,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        deletion_indicator=deletion_indicator,
    )


@router.patch("/{row_id}", response_model=CustomerForwarderOut)
def update_customer_forwarder_api(
    row_id: int,
    payload: CustomerForwarderUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    try:
        obj = update_customer_forwarder(db, row_id, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_forwarder_api(
    row_id: int,
    request: Request,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    ok = delete_customer_forwarder(db, row_id, mode=mode, current_user_email=user_email)
    if not ok:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    return None


@router.delete("/unlink", status_code=status.HTTP_204_NO_CONTENT)
def unlink_customer_forwarder_api(
    request: Request,
    customer_id: int = Query(..., ge=1),
    forwarder_id: int = Query(..., ge=1),
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    ok = delete_customer_forwarder_by_pair(
        db, customer_id, forwarder_id, mode=mode, current_user_email=user_email
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    return None


@router.get("/search/customers", response_model=list[SearchResult])
def search_customers_api(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return search_customers(db, q)


@router.get("/search/forwarders", response_model=list[SearchResult])
def search_forwarders_api(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return search_forwarders(db, q)
