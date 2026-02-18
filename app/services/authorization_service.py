from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.user_roles import UserRole
from app.models.users import User


def _normalize_tokens(values: Iterable[str] | None) -> set[str]:
    if values is None:
        return set()
    normalized: set[str] = set()
    for value in values:
        token = str(value or "").strip().lower()
        if token:
            normalized.add(token)
    return normalized


def user_has_any_permission(
    db: Session,
    *,
    user_email: str | None,
    action_keys: Iterable[str] | None,
    object_types: Iterable[str] | None,
) -> bool:
    email = (user_email or "").strip().lower()
    if not email:
        return False

    normalized_actions = _normalize_tokens(action_keys)
    normalized_objects = _normalize_tokens(object_types)
    if not normalized_actions or not normalized_objects:
        return False

    row = (
        db.query(RolePermission.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .join(User, User.id == UserRole.user_id)
        .filter(func.lower(User.email) == email)
        .filter(func.lower(Permission.action_key).in_(sorted(normalized_actions)))
        .filter(func.lower(Permission.object_type).in_(sorted(normalized_objects)))
        .first()
    )
    return row is not None
