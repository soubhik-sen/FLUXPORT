from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.partner_role import PartnerRole
from app.schemas.partner_type import PartnerTypeCreate, PartnerTypeUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (role_code)."""


def create_partner_type(db: Session, data: PartnerTypeCreate) -> PartnerRole:
    obj = PartnerRole(
        role_code=data.role_code,
        role_name=data.role_name,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Partner type already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_partner_type(db: Session, type_id: int) -> PartnerRole | None:
    return db.get(PartnerRole, type_id)


def list_partner_types(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
) -> list[PartnerRole]:
    stmt = select(PartnerRole).offset(skip).limit(limit).order_by(PartnerRole.id.desc())
    if is_active is not None:
        stmt = stmt.where(PartnerRole.is_active == is_active)
    return list(db.execute(stmt).scalars().all())


def update_partner_type(db: Session, type_id: int, data: PartnerTypeUpdate) -> PartnerRole | None:
    obj = db.get(PartnerRole, type_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint.") from e

    db.refresh(obj)
    return obj


def delete_partner_type(db: Session, type_id: int, mode: str = "soft") -> bool:
    obj = db.get(PartnerRole, type_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.is_active = False
    db.commit()
    return True
