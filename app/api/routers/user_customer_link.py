from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.crud.user_customer_link import (
    DuplicateError,
    create_user_customer_link,
    delete_user_customer_link,
    get_user_customer_link,
    get_user_customer_link_by_pair,
    list_user_customer_links,
    search_customers,
    search_users,
    update_user_customer_link,
)
from app.db.session import get_db
from app.schemas.user_customer_link import (
    CustomerSearchResult,
    UserSearchResult,
    UserCustomerLinkCreate,
    UserCustomerLinkOut,
    UserCustomerLinkUpdate,
)

router = APIRouter(prefix="/user-customers", tags=["user-customers"])


def _get_user_email(request: Request) -> str:
    return request.headers.get("X-User-Email") or request.headers.get("X-User") or "system@local"


@router.post("", response_model=UserCustomerLinkOut, status_code=status.HTTP_201_CREATED)
def create_user_customer_link_api(
    payload: UserCustomerLinkCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        return create_user_customer_link(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=UserCustomerLinkOut)
def get_user_customer_link_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_user_customer_link(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User-customer link not found")
    return obj


@router.get("", response_model=list[UserCustomerLinkOut])
def list_user_customer_links_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_email: str | None = Query(None),
    customer_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_user_customer_links(
        db,
        skip=skip,
        limit=limit,
        user_email=user_email,
        customer_id=customer_id,
        deletion_indicator=deletion_indicator,
    )


@router.patch("/{row_id}", response_model=UserCustomerLinkOut)
def update_user_customer_link_api(
    row_id: int,
    payload: UserCustomerLinkUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    try:
        obj = update_user_customer_link(db, row_id, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="User-customer link not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_customer_link_api(
    row_id: int,
    request: Request,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    ok = delete_user_customer_link(db, row_id, mode=mode, current_user_email=user_email)
    if not ok:
        raise HTTPException(status_code=404, detail="User-customer link not found")
    return None


@router.get("/search/users", response_model=list[UserSearchResult])
def search_users_api(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return search_users(db, q)


@router.get("/search/customers", response_model=list[CustomerSearchResult])
def search_customers_api(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return search_customers(db, q)
