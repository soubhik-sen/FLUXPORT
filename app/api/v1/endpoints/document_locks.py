from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps.request_identity import get_request_identity_with_db
from app.core.config import settings
from app.db.session import get_db
from app.models.purchase_order import PurchaseOrderHeader
from app.schemas.document_lock import (
    DocumentLockAcquireRequest,
    DocumentLockAcquireResponse,
    DocumentLockForceReleaseRequest,
    DocumentLockHeartbeatResponse,
    DocumentLockListResponse,
    DocumentLockReleaseResponse,
    DocumentLockTokenRequest,
    DocumentLockView,
)
from app.schemas.request_identity import RequestIdentity
from app.services.document_lock_service import DocumentLockFailure, DocumentLockService
from app.services.role_scope_policy import (
    is_scope_denied,
    sanitize_scope_by_field,
    scope_deny_detail,
)

router = APIRouter()


def _raise_lock_failure(exc: DocumentLockFailure) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())


def _require_identity_email(identity: RequestIdentity) -> str:
    email = (identity.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Authenticated email is required.")
    return email


def _require_admin_org(identity: RequestIdentity) -> str:
    email = _require_identity_email(identity)
    role_names = {(role or "").strip().upper() for role in (identity.role_names or [])}
    if "ADMIN_ORG" not in role_names:
        raise HTTPException(status_code=403, detail="ADMIN_ORG role is required.")
    return email


def _ensure_document_scope_access(
    db: Session,
    *,
    object_type: str,
    document_id: int,
    user_email: str,
) -> None:
    if object_type == "PURCHASE_ORDER":
        from app.api.v1.endpoints.purchase_orders import (
            _is_po_in_scope,
            _legacy_company_ids_for_customer_scope,
            _resolve_po_scope_by_field,
        )

        po = db.query(PurchaseOrderHeader).filter(PurchaseOrderHeader.id == document_id).first()
        if po is None:
            raise HTTPException(status_code=404, detail="Purchase Order not found.")

        raw_scope = _resolve_po_scope_by_field(db, user_email)
        if is_scope_denied(raw_scope):
            raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
        scope_by_field = sanitize_scope_by_field(raw_scope)
        legacy_company_ids = _legacy_company_ids_for_customer_scope(db, scope_by_field)
        if not _is_po_in_scope(
            po,
            scope_by_field,
            legacy_customer_company_ids=legacy_company_ids,
        ):
            raise HTTPException(status_code=403, detail="Purchase Order is outside user scope")
        return

    from app.api.v1.endpoints.shipments import _resolve_shipment_scope, _shipment_is_in_scope

    raw_scope = _resolve_shipment_scope(
        db,
        user_email,
        endpoint_key="shipments.workspace",
        http_method="GET",
        endpoint_path=f"/api/v1/shipments/workspace/{document_id}",
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
    scope_by_field = sanitize_scope_by_field(raw_scope)
    if not _shipment_is_in_scope(db, int(document_id), scope_by_field):
        raise HTTPException(status_code=403, detail="Shipment is outside user scope")


def _to_lock_view(lock) -> DocumentLockView:
    return DocumentLockView(
        lock_id=int(lock.id),
        object_type=str(lock.object_type),
        document_id=int(lock.document_id),
        owner_email=str(lock.owner_email),
        owner_session_id=str(lock.owner_session_id),
        acquired_at=lock.acquired_at,
        heartbeat_at=lock.heartbeat_at,
        expires_at=lock.expires_at,
        is_active=bool(lock.is_active),
        release_reason=lock.release_reason,
    )


@router.post(
    "/acquire",
    response_model=DocumentLockAcquireResponse,
    status_code=status.HTTP_200_OK,
)
def acquire_document_lock(
    payload: DocumentLockAcquireRequest,
    request: Request,
    db: Session = Depends(get_db),
    identity: RequestIdentity = Depends(get_request_identity_with_db),
):
    del request
    user_email = _require_identity_email(identity)
    _ensure_document_scope_access(
        db,
        object_type=payload.object_type,
        document_id=payload.document_id,
        user_email=user_email,
    )
    service = DocumentLockService(db)
    try:
        result = service.acquire_lock(
            object_type=payload.object_type,
            document_id=payload.document_id,
            owner_email=user_email,
            owner_session_id=payload.session_id,
        )
        db.commit()
    except DocumentLockFailure as exc:
        db.rollback()
        _raise_lock_failure(exc)

    return DocumentLockAcquireResponse(
        lock_id=int(result.lock.id),
        object_type=str(result.lock.object_type),
        document_id=int(result.lock.document_id),
        owner_email=str(result.lock.owner_email),
        acquired_at=result.lock.acquired_at,
        expires_at=result.lock.expires_at,
        ttl_seconds=max(30, int(settings.DOCUMENT_EDIT_LOCK_TTL_SECONDS)),
        lock_token=result.lock_token,
    )


@router.post("/heartbeat", response_model=DocumentLockHeartbeatResponse)
def heartbeat_document_lock(
    payload: DocumentLockTokenRequest,
    db: Session = Depends(get_db),
    identity: RequestIdentity = Depends(get_request_identity_with_db),
):
    user_email = _require_identity_email(identity)
    service = DocumentLockService(db)
    try:
        lock = service.heartbeat(lock_token=payload.lock_token, owner_email=user_email)
        _ensure_document_scope_access(
            db,
            object_type=str(lock.object_type),
            document_id=int(lock.document_id),
            user_email=user_email,
        )
        db.commit()
    except DocumentLockFailure as exc:
        db.rollback()
        _raise_lock_failure(exc)
    return DocumentLockHeartbeatResponse(
        lock_id=int(lock.id),
        expires_at=lock.expires_at,
        ttl_seconds=max(30, int(settings.DOCUMENT_EDIT_LOCK_TTL_SECONDS)),
    )


@router.post("/release", response_model=DocumentLockReleaseResponse)
def release_document_lock(
    payload: DocumentLockTokenRequest,
    db: Session = Depends(get_db),
    identity: RequestIdentity = Depends(get_request_identity_with_db),
):
    user_email = _require_identity_email(identity)
    service = DocumentLockService(db)
    try:
        lock = service.release(lock_token=payload.lock_token, owner_email=user_email)
        if lock is not None:
            _ensure_document_scope_access(
                db,
                object_type=str(lock.object_type),
                document_id=int(lock.document_id),
                user_email=user_email,
            )
        db.commit()
    except DocumentLockFailure as exc:
        db.rollback()
        _raise_lock_failure(exc)

    if lock is None:
        return DocumentLockReleaseResponse(
            lock_id=None,
            released=False,
            message="No active lock found for the provided token.",
        )
    return DocumentLockReleaseResponse(
        lock_id=int(lock.id),
        released=True,
        message="Lock released.",
    )


@router.get("/active", response_model=DocumentLockListResponse)
def list_active_document_locks(
    db: Session = Depends(get_db),
    identity: RequestIdentity = Depends(get_request_identity_with_db),
):
    _require_admin_org(identity)
    service = DocumentLockService(db)
    locks = service.list_active_locks()
    db.commit()
    return DocumentLockListResponse(active_locks=[_to_lock_view(lock) for lock in locks])


@router.post("/force-release", response_model=DocumentLockReleaseResponse)
def force_release_document_lock(
    payload: DocumentLockForceReleaseRequest,
    db: Session = Depends(get_db),
    identity: RequestIdentity = Depends(get_request_identity_with_db),
):
    admin_email = _require_admin_org(identity)
    service = DocumentLockService(db)
    try:
        lock = service.force_release(
            lock_id=payload.lock_id,
            admin_email=admin_email,
            reason=payload.reason,
        )
        db.commit()
    except DocumentLockFailure as exc:
        db.rollback()
        _raise_lock_failure(exc)

    return DocumentLockReleaseResponse(
        lock_id=int(lock.id),
        released=True,
        message="Lock force-released.",
    )
