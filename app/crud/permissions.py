from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.permissions import Permission
from app.schemas.permissions import PermissionCreate, PermissionUpdate


class DuplicateError(Exception):
    """Raised when unique constraint is violated (uq_permissions_action_object)."""


def create_permission(db: Session, data: PermissionCreate) -> Permission:
    obj = Permission(action_key=data.action_key, object_type=data.object_type)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Permission already exists (action_key + object_type must be unique).") from e
    db.refresh(obj)
    return obj


def get_permission(db: Session, permission_id: int) -> Permission | None:
    return db.get(Permission, permission_id)


def list_permissions(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    action_key: str | None = None,
    object_type: str | None = None,
) -> list[Permission]:
    stmt = select(Permission).offset(skip).limit(limit).order_by(Permission.id.desc())
    if action_key:
        stmt = stmt.where(Permission.action_key == action_key)
    if object_type:
        stmt = stmt.where(Permission.object_type == object_type)
    return list(db.execute(stmt).scalars().all())


def update_permission(db: Session, permission_id: int, data: PermissionUpdate) -> Permission | None:
    obj = db.get(Permission, permission_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (action_key + object_type).") from e

    db.refresh(obj)
    return obj


def delete_permission(db: Session, permission_id: int) -> bool:
    obj = db.get(Permission, permission_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
