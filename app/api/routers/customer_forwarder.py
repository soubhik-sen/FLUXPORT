from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.crud.customer_forwarder import (
    count_customer_forwarders,
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
from app.services.role_scope_policy import (
    is_scope_denied,
    resolve_scope_by_field,
    sanitize_scope_by_field,
    scope_deny_detail,
)
from app.services.user_scope_service import resolve_union_scope_ids
from app.api.deps.request_identity import get_request_email

router = APIRouter(prefix="/customer-forwarders", tags=["customer-forwarders"])


def _get_user_email(request: Request) -> str:
    return get_request_email(request)


def _enforce_policy(request: Request, db: Session) -> None:
    raw_scope = resolve_scope_by_field(
        db,
        user_email=_get_user_email(request),
        endpoint_key="admin.customer_forwarders",
        http_method=request.method,
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))


def _resolve_forwarder_scope(
    request: Request, db: Session
) -> tuple[str, bool, bool, set[int]]:
    user_email = _get_user_email(request)
    raw_scope = resolve_scope_by_field(
        db,
        user_email=user_email,
        endpoint_key="admin.customer_forwarders",
        http_method=request.method,
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))

    scope_by_field = sanitize_scope_by_field(raw_scope)
    role_names = resolve_union_scope_ids(db, user_email).role_names
    is_admin_org = "ADMIN_ORG" in role_names
    has_forwarder_role = "FORWARDER" in role_names
    allowed_forwarder_ids = set(scope_by_field.get("forwarder_id") or set())

    if not is_admin_org and has_forwarder_role and not allowed_forwarder_ids:
        raise HTTPException(
            status_code=403,
            detail="Forwarder user has no scoped forwarder mappings.",
        )
    return user_email, is_admin_org, has_forwarder_role, allowed_forwarder_ids


def _enforce_forwarder_write_scope(
    *,
    forwarder_id: int,
    is_admin_org: bool,
    has_forwarder_role: bool,
    allowed_forwarder_ids: set[int],
) -> None:
    if is_admin_org or not has_forwarder_role:
        return
    if forwarder_id not in allowed_forwarder_ids:
        raise HTTPException(
            status_code=403,
            detail="Forwarder can only manage customer links for its own forwarder scope.",
        )


def _enforce_forwarder_row_scope(
    *,
    row_forwarder_id: int,
    is_admin_org: bool,
    has_forwarder_role: bool,
    allowed_forwarder_ids: set[int],
) -> None:
    if is_admin_org or not has_forwarder_role:
        return
    if row_forwarder_id not in allowed_forwarder_ids:
        raise HTTPException(
            status_code=403,
            detail="Requested row is outside forwarder scope.",
        )


@router.post("", response_model=CustomerForwarderOut, status_code=status.HTTP_201_CREATED)
def create_customer_forwarder_api(
    payload: CustomerForwarderCreate, request: Request, db: Session = Depends(get_db)
):
    user_email, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    _enforce_forwarder_write_scope(
        forwarder_id=payload.forwarder_id,
        is_admin_org=is_admin_org,
        has_forwarder_role=has_forwarder_role,
        allowed_forwarder_ids=allowed_forwarder_ids,
    )
    try:
        return create_customer_forwarder(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/link", response_model=CustomerForwarderOut, status_code=status.HTTP_201_CREATED)
def link_customer_forwarder_api(
    payload: CustomerForwarderCreate, request: Request, db: Session = Depends(get_db)
):
    user_email, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    _enforce_forwarder_write_scope(
        forwarder_id=payload.forwarder_id,
        is_admin_org=is_admin_org,
        has_forwarder_role=has_forwarder_role,
        allowed_forwarder_ids=allowed_forwarder_ids,
    )
    existing = get_customer_forwarder_by_pair(db, payload.customer_id, payload.forwarder_id)
    if existing:
        return existing
    try:
        return create_customer_forwarder(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=CustomerForwarderOut)
def get_customer_forwarder_api(
    row_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    obj = get_customer_forwarder(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    _enforce_forwarder_row_scope(
        row_forwarder_id=obj.forwarder_id,
        is_admin_org=is_admin_org,
        has_forwarder_role=has_forwarder_role,
        allowed_forwarder_ids=allowed_forwarder_ids,
    )
    return obj


@router.get("", response_model=list[CustomerForwarderOut])
def list_customer_forwarders_api(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    customer_id: int | None = Query(None, ge=1),
    forwarder_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    _, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    scoped_forwarder_ids: set[int] | None = None
    if not is_admin_org and has_forwarder_role:
        if forwarder_id is not None and forwarder_id not in allowed_forwarder_ids:
            raise HTTPException(status_code=403, detail="Requested forwarder is outside scope")
        scoped_forwarder_ids = allowed_forwarder_ids
    return list_customer_forwarders_with_names(
        db,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        forwarder_ids=scoped_forwarder_ids,
        deletion_indicator=deletion_indicator,
    )


@router.get("/paged/list")
def list_customer_forwarders_paged_api(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    customer_id: int | None = Query(None, ge=1),
    forwarder_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    _, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    scoped_forwarder_ids: set[int] | None = None
    if not is_admin_org and has_forwarder_role:
        if forwarder_id is not None and forwarder_id not in allowed_forwarder_ids:
            raise HTTPException(status_code=403, detail="Requested forwarder is outside scope")
        scoped_forwarder_ids = allowed_forwarder_ids
    items = list_customer_forwarders_with_names(
        db,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        forwarder_ids=scoped_forwarder_ids,
        deletion_indicator=deletion_indicator,
    )
    total = count_customer_forwarders(
        db,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        forwarder_ids=scoped_forwarder_ids,
        deletion_indicator=deletion_indicator,
    )
    return {
        "items": [
            CustomerForwarderOut.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.patch("/{row_id}", response_model=CustomerForwarderOut)
def update_customer_forwarder_api(
    row_id: int,
    payload: CustomerForwarderUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    existing = get_customer_forwarder(db, row_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    _enforce_forwarder_row_scope(
        row_forwarder_id=existing.forwarder_id,
        is_admin_org=is_admin_org,
        has_forwarder_role=has_forwarder_role,
        allowed_forwarder_ids=allowed_forwarder_ids,
    )
    if payload.forwarder_id is not None:
        _enforce_forwarder_write_scope(
            forwarder_id=payload.forwarder_id,
            is_admin_org=is_admin_org,
            has_forwarder_role=has_forwarder_role,
            allowed_forwarder_ids=allowed_forwarder_ids,
        )
    try:
        obj = update_customer_forwarder(db, row_id, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_forwarder_api(
    row_id: int,
    request: Request,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    user_email, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    existing = get_customer_forwarder(db, row_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    _enforce_forwarder_row_scope(
        row_forwarder_id=existing.forwarder_id,
        is_admin_org=is_admin_org,
        has_forwarder_role=has_forwarder_role,
        allowed_forwarder_ids=allowed_forwarder_ids,
    )
    ok = delete_customer_forwarder(db, row_id, mode=mode, current_user_email=user_email)
    return None


@router.delete("/unlink", status_code=status.HTTP_204_NO_CONTENT)
def unlink_customer_forwarder_api(
    request: Request,
    customer_id: int = Query(..., ge=1),
    forwarder_id: int = Query(..., ge=1),
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    user_email, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    _enforce_forwarder_write_scope(
        forwarder_id=forwarder_id,
        is_admin_org=is_admin_org,
        has_forwarder_role=has_forwarder_role,
        allowed_forwarder_ids=allowed_forwarder_ids,
    )
    ok = delete_customer_forwarder_by_pair(
        db, customer_id, forwarder_id, mode=mode, current_user_email=user_email
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Customer-forwarder map not found")
    return None


@router.get("/search/customers", response_model=list[SearchResult])
def search_customers_api(
    request: Request,
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    _resolve_forwarder_scope(request, db)
    return search_customers(db, q)


@router.get("/search/forwarders", response_model=list[SearchResult])
def search_forwarders_api(
    request: Request,
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    _, is_admin_org, has_forwarder_role, allowed_forwarder_ids = _resolve_forwarder_scope(
        request, db
    )
    rows = search_forwarders(db, q)
    if is_admin_org or not has_forwarder_role:
        return rows
    return [row for row in rows if row.get("id") in allowed_forwarder_ids]
