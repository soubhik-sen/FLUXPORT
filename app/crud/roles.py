from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.roles import Role
from app.schemas.roles import RoleCreate, RoleUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (uq_roles_name)."""


def create_role(db: Session, data: RoleCreate) -> Role:
    obj = Role(name=data.name)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Role already exists (name must be unique).") from e
    db.refresh(obj)
    return obj


def get_role(db: Session, role_id: int) -> Role | None:
    return db.get(Role, role_id)


def list_roles(db: Session, skip: int = 0, limit: int = 50, name: str | None = None) -> list[Role]:
    stmt = select(Role).offset(skip).limit(limit).order_by(Role.id.desc())
    if name:
        stmt = stmt.where(Role.name.ilike(f"%{name}%"))
    return list(db.execute(stmt).scalars().all())


def update_role(db: Session, role_id: int, data: RoleUpdate) -> Role | None:
    obj = db.get(Role, role_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (name must be unique).") from e

    db.refresh(obj)
    return obj


def delete_role(db: Session, role_id: int) -> bool:
    obj = db.get(Role, role_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
