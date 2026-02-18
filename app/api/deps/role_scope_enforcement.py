from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps.request_identity import get_request_email
from app.db.session import get_db
from app.services.role_scope_policy import (
    is_scope_denied,
    resolve_scope_by_field,
    scope_deny_detail,
)


def enforce_role_scope_policy_access(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """
    Global policy gate:
    - evaluates role-scope policy for the current method/path
    - blocks request when policy decision is deny

    Endpoint-specific row/payload scoping remains implemented inside routers.
    """
    user_email = get_request_email(request)
    raw_scope = resolve_scope_by_field(
        db,
        user_email=user_email,
        endpoint_key=None,
        http_method=request.method,
        endpoint_path=request.url.path,
    )
    if is_scope_denied(raw_scope):
        raise HTTPException(status_code=403, detail=scope_deny_detail(raw_scope))
