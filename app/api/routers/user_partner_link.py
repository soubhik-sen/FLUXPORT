from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.crud.user_partner_link import (
    count_user_partner_links,
    DuplicateError,
    create_user_partner_link,
    delete_user_partner_link,
    get_user_partner_link,
    get_user_partner_link_by_pair,
    list_user_partner_links,
    search_partners,
    search_users,
    update_user_partner_link,
)
from app.db.session import get_db
from app.schemas.user_partner_link import (
    PartnerSearchResult,
    UserSearchResult,
    UserPartnerLinkCreate,
    UserPartnerLinkOut,
    UserPartnerLinkUpdate,
)
from app.services.role_scope_policy import (
    is_scope_denied,
    resolve_scope_by_field,
    scope_deny_detail,
)
from app.api.deps.request_identity import get_request_email

router = APIRouter(prefix="/user-partners", tags=["user-partners"])


def _get_user_email(request: Request) -> str:
    return get_request_email(request)


def _enforce_policy(request: Request, db: Session) -> None:
    raw_scope = resolve_scope_by_field(
        db,
        user_email=_get_user_email(request),
        endpoint_key="admin.user_partners",
        http_method=request.method,
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))


@router.post("", response_model=UserPartnerLinkOut, status_code=status.HTTP_201_CREATED)
def create_user_partner_link_api(
    payload: UserPartnerLinkCreate, request: Request, db: Session = Depends(get_db)
):
    _enforce_policy(request, db)
    user_email = _get_user_email(request)
    try:
        return create_user_partner_link(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=UserPartnerLinkOut)
def get_user_partner_link_api(row_id: int, request: Request, db: Session = Depends(get_db)):
    _enforce_policy(request, db)
    obj = get_user_partner_link(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User-partner link not found")
    return obj


@router.get("", response_model=list[UserPartnerLinkOut])
def list_user_partner_links_api(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_email: str | None = Query(None),
    partner_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    _enforce_policy(request, db)
    return list_user_partner_links(
        db,
        skip=skip,
        limit=limit,
        user_email=user_email,
        partner_id=partner_id,
        deletion_indicator=deletion_indicator,
    )


@router.get("/paged/list")
def list_user_partner_links_paged_api(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_email: str | None = Query(None),
    partner_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    _enforce_policy(request, db)
    items = list_user_partner_links(
        db,
        skip=skip,
        limit=limit,
        user_email=user_email,
        partner_id=partner_id,
        deletion_indicator=deletion_indicator,
    )
    total = count_user_partner_links(
        db,
        user_email=user_email,
        partner_id=partner_id,
        deletion_indicator=deletion_indicator,
    )
    return {
        "items": [
            UserPartnerLinkOut.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.patch("/{row_id}", response_model=UserPartnerLinkOut)
def update_user_partner_link_api(
    row_id: int,
    payload: UserPartnerLinkUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    _enforce_policy(request, db)
    user_email = _get_user_email(request)
    try:
        obj = update_user_partner_link(db, row_id, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="User-partner link not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_partner_link_api(
    row_id: int,
    request: Request,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    _enforce_policy(request, db)
    user_email = _get_user_email(request)
    ok = delete_user_partner_link(db, row_id, mode=mode, current_user_email=user_email)
    if not ok:
        raise HTTPException(status_code=404, detail="User-partner link not found")
    return None


@router.get("/search/users", response_model=list[UserSearchResult])
def search_users_api(request: Request, q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    _enforce_policy(request, db)
    return search_users(db, q)


@router.get("/search/partners", response_model=list[PartnerSearchResult])
def search_partners_api(request: Request, q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    _enforce_policy(request, db)
    return search_partners(db, q)
