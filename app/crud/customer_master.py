from __future__ import annotations

from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer_master import CustomerMaster
from app.schemas.customer_master import CustomerMasterCreate, CustomerMasterUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (identifier or tax id)."""


def create_customer_master(db: Session, data: CustomerMasterCreate) -> CustomerMaster:
    obj = CustomerMaster(
        customer_identifier=data.customer_identifier,
        role_id=data.role_id,
        legal_name=data.legal_name,
        trade_name=data.trade_name,
        tax_registration_id=data.tax_registration_id,
        payment_terms_code=data.payment_terms_code,
        preferred_currency=data.preferred_currency,
        is_active=data.is_active,
        is_verified=data.is_verified,
        addr_id=data.addr_id,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Customer already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_customer_master(db: Session, customer_id: int) -> CustomerMaster | None:
    return db.get(CustomerMaster, customer_id)


def list_customer_master(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
    role_id: int | None = None,
    q: str | None = None,
) -> list[CustomerMaster]:
    stmt = select(CustomerMaster).offset(skip).limit(limit).order_by(CustomerMaster.id.desc())
    if is_active is not None:
        stmt = stmt.where(CustomerMaster.is_active == is_active)
    if role_id is not None:
        stmt = stmt.where(CustomerMaster.role_id == role_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                CustomerMaster.customer_identifier.ilike(like),
                CustomerMaster.legal_name.ilike(like),
                CustomerMaster.trade_name.ilike(like),
            )
        )
    return list(db.execute(stmt).scalars().all())


def update_customer_master(db: Session, customer_id: int, data: CustomerMasterUpdate) -> CustomerMaster | None:
    obj = db.get(CustomerMaster, customer_id)
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


def delete_customer_master(db: Session, customer_id: int, mode: str = "soft") -> bool:
    obj = db.get(CustomerMaster, customer_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.is_active = False
    db.commit()
    return True
