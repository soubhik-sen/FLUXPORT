from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.users import User
from app.schemas.request_identity import RequestIdentity
from app.services.user_scope_service import list_user_roles


def attach_internal_user_context(
    db: Session,
    *,
    identity: RequestIdentity,
) -> RequestIdentity:
    """
    Best-effort user mapping from trusted identity claims to local user record.
    Missing local user is allowed to preserve compatibility in transition mode.
    """
    email = (identity.email or "").strip().lower()
    if not email:
        return identity

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        return identity

    roles = list_user_roles(db, user.id)
    role_names = sorted(
        {
            (role.name or "").strip().upper()
            for role in roles
            if role and role.name
        }
    )
    return identity.model_copy(
        update={
            "user_id": int(user.id),
            "role_names": role_names,
        }
    )
