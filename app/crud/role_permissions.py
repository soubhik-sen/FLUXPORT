from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.role_permissions import RolePermission
from app.schemas.role_permissions import RolePermissionCreate, RolePermissionUpdate


class DuplicateError(Exception):
    """Raised when unique constraint is violated (uq_role_permissions_role_perm)."""


def create_role_permission(db: Session, data: RolePermissionCreate) -> RolePermission:
    obj = RolePermission(
        role_id=data.role_id,
        permission_id=data.permission_id,
        role_name=data.role_name,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Mapping already exists (role_id + permission_id must be unique).") from e
    db.refresh(obj)
    return obj


def get_role_permission(db: Session, row_id: int) -> RolePermission | None:
    return db.get(RolePermission, row_id)


def list_role_permissions(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    role_id: int | None = None,
    permission_id: int | None = None,
    role_name: str | None = None,
) -> list[RolePermission]:
    stmt = select(RolePermission).offset(skip).limit(limit).order_by(RolePermission.id.desc())

    if role_id is not None:
        stmt = stmt.where(RolePermission.role_id == role_id)
    if permission_id is not None:
        stmt = stmt.where(RolePermission.permission_id == permission_id)
    if role_name is not None:
        stmt = stmt.where(RolePermission.role_name.ilike(f"%{role_name}%"))

    return list(db.execute(stmt).scalars().all())


def update_role_permission(db: Session, row_id: int, data: RolePermissionUpdate) -> RolePermission | None:
    obj = db.get(RolePermission, row_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (role_id + permission_id).") from e

    db.refresh(obj)
    return obj


def delete_role_permission(db: Session, row_id: int) -> bool:
    obj = db.get(RolePermission, row_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
