from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.object_types import ObjectType
from app.schemas.object_types import ObjectTypeCreate, ObjectTypeUpdate


class DuplicateError(Exception):
    """Raised when PK/unique constraint is violated (object_type)."""


def create_object_type(db: Session, data: ObjectTypeCreate) -> ObjectType:
    obj = ObjectType(object_type=data.object_type, object_description=data.object_description)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Object type already exists (object_type is primary key).") from e
    db.refresh(obj)
    return obj


def get_object_type(db: Session, object_type: str) -> ObjectType | None:
    return db.get(ObjectType, object_type)


def list_object_types(db: Session, skip: int = 0, limit: int = 50, q: str | None = None) -> list[ObjectType]:
    stmt = select(ObjectType).offset(skip).limit(limit).order_by(ObjectType.object_type.asc())
    if q:
        stmt = stmt.where(ObjectType.object_description.ilike(f"%{q}%"))
    return list(db.execute(stmt).scalars().all())


def update_object_type(db: Session, object_type: str, data: ObjectTypeUpdate) -> ObjectType | None:
    obj = db.get(ObjectType, object_type)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)

    # If you change the PK (object_type), do it carefully.
    # For now: allow updating description only if you prefer stricter behavior.
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates PK/unique constraint (object_type).") from e

    db.refresh(obj)
    return obj


def delete_object_type(db: Session, object_type: str) -> bool:
    obj = db.get(ObjectType, object_type)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
