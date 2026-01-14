from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_countries import UserCountry
from app.schemas.user_countries import UserCountryCreate, UserCountryUpdate


class DuplicateError(Exception):
    """Raised when unique constraint is violated (uq_user_countries_user_country)."""


def create_user_country(db: Session, data: UserCountryCreate) -> UserCountry:
    obj = UserCountry(user_id=data.user_id, country_code=data.country_code.upper())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Mapping already exists (user_id + country_code must be unique).") from e
    db.refresh(obj)
    return obj


def get_user_country(db: Session, row_id: int) -> UserCountry | None:
    return db.get(UserCountry, row_id)


def list_user_countries(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = None,
    country_code: str | None = None,
) -> list[UserCountry]:
    stmt = select(UserCountry).offset(skip).limit(limit).order_by(UserCountry.id.desc())

    if user_id is not None:
        stmt = stmt.where(UserCountry.user_id == user_id)
    if country_code is not None:
        stmt = stmt.where(UserCountry.country_code == country_code.upper())

    return list(db.execute(stmt).scalars().all())


def update_user_country(db: Session, row_id: int, data: UserCountryUpdate) -> UserCountry | None:
    obj = db.get(UserCountry, row_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    if "country_code" in patch and patch["country_code"] is not None:
        patch["country_code"] = patch["country_code"].upper()

    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (user_id + country_code).") from e

    db.refresh(obj)
    return obj


def delete_user_country(db: Session, row_id: int) -> bool:
    obj = db.get(UserCountry, row_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
