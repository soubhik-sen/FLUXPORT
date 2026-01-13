from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (e.g., email unique)."""


def create_user(db: Session, data: UserCreate) -> User:
    obj = User(
        username=data.username,
        email=str(data.email),
        clearance=data.clearance,
        is_active=data.is_active,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("User already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalar_one_or_none()


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
) -> list[User]:
    stmt = select(User).offset(skip).limit(limit).order_by(User.id.desc())
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    return list(db.execute(stmt).scalars().all())


def update_user(db: Session, user_id: int, data: UserUpdate) -> User | None:
    obj = db.get(User, user_id)
    if not obj:
        return None

    # only apply fields that were provided
    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        if k == "email" and v is not None:
            v = str(v)
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint.") from e

    db.refresh(obj)
    return obj


def delete_user(db: Session, user_id: int, mode: str = "soft") -> bool:
    """
    mode:
      - "soft": sets is_active=False
      - "hard": deletes the row
    Returns True if something was deleted/updated, else False if not found.
    """
    obj = db.get(User, user_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    # soft delete
    obj.is_active = False
    db.commit()
    return True
