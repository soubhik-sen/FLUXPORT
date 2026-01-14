from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_roles import UserRole
from app.schemas.user_roles import UserRoleCreate, UserRoleUpdate


class DuplicateError(Exception):
    """Raised when unique constraint is violated (uq_user_roles_user_role)."""


def create_user_role(db: Session, data: UserRoleCreate) -> UserRole:
    obj = UserRole(user_id=data.user_id, role_id=data.role_id)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Mapping already exists (user_id + role_id must be unique).") from e
    db.refresh(obj)
    return obj


def get_user_role(db: Session, row_id: int) -> UserRole | None:
    return db.get(UserRole, row_id)


def list_user_roles(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = None,
    role_id: int | None = None,
) -> list[UserRole]:
    stmt = select(UserRole).offset(skip).limit(limit).order_by(UserRole.id.desc())

    if user_id is not None:
        stmt = stmt.where(UserRole.user_id == user_id)
    if role_id is not None:
        stmt = stmt.where(UserRole.role_id == role_id)

    return list(db.execute(stmt).scalars().all())


def update_user_role(db: Session, row_id: int, data: UserRoleUpdate) -> UserRole | None:
    obj = db.get(UserRole, row_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (user_id + role_id).") from e

    db.refresh(obj)
    return obj


def delete_user_role(db: Session, row_id: int) -> bool:
    obj = db.get(UserRole, row_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
