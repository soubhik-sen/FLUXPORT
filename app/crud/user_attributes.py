from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_attributes import UserAttribute
from app.schemas.user_attributes import UserAttributeCreate, UserAttributeUpdate


class DuplicateError(Exception):
    """Raised when unique constraint is violated (uq_user_attributes_user_key)."""


def create_user_attribute(db: Session, data: UserAttributeCreate) -> UserAttribute:
    obj = UserAttribute(user_id=data.user_id, key=data.key, value=data.value)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Attribute already exists (user_id + key must be unique).") from e
    db.refresh(obj)
    return obj


def get_user_attribute(db: Session, row_id: int) -> UserAttribute | None:
    return db.get(UserAttribute, row_id)


def list_user_attributes(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = None,
    key: str | None = None,
) -> list[UserAttribute]:
    stmt = select(UserAttribute).offset(skip).limit(limit).order_by(UserAttribute.id.desc())

    if user_id is not None:
        stmt = stmt.where(UserAttribute.user_id == user_id)
    if key is not None:
        stmt = stmt.where(UserAttribute.key == key)

    return list(db.execute(stmt).scalars().all())


def update_user_attribute(db: Session, row_id: int, data: UserAttributeUpdate) -> UserAttribute | None:
    obj = db.get(UserAttribute, row_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (user_id + key).") from e

    db.refresh(obj)
    return obj


def delete_user_attribute(db: Session, row_id: int) -> bool:
    obj = db.get(UserAttribute, row_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
