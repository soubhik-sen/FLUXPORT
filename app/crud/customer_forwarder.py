from __future__ import annotations

from sqlalchemy import select, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.customer_master import CustomerMaster
from app.models.customer_forwarder import CustomerForwarder
from app.models.partner_master import PartnerMaster
from app.schemas.customer_forwarder import CustomerForwarderCreate, CustomerForwarderUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (customer_id + forwarder_id)."""


def create_customer_forwarder(
    db: Session, data: CustomerForwarderCreate, current_user_email: str
) -> CustomerForwarder:
    obj = CustomerForwarder(
        customer_id=data.customer_id,
        forwarder_id=data.forwarder_id,
        deletion_indicator=data.deletion_indicator,
        created_by=current_user_email,
        last_changed_by=current_user_email,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Customer-forwarder map already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_customer_forwarder(db: Session, row_id: int) -> CustomerForwarder | None:
    return db.get(CustomerForwarder, row_id)


def get_customer_forwarder_by_pair(
    db: Session, customer_id: int, forwarder_id: int
) -> CustomerForwarder | None:
    stmt = select(CustomerForwarder).where(
        CustomerForwarder.customer_id == customer_id,
        CustomerForwarder.forwarder_id == forwarder_id,
    )
    return db.execute(stmt).scalars().first()


def list_customer_forwarders(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    customer_id: int | None = None,
    forwarder_id: int | None = None,
    deletion_indicator: bool | None = None,
) -> list[CustomerForwarder]:
    stmt = select(CustomerForwarder).offset(skip).limit(limit).order_by(CustomerForwarder.id.desc())
    if customer_id is not None:
        stmt = stmt.where(CustomerForwarder.customer_id == customer_id)
    if forwarder_id is not None:
        stmt = stmt.where(CustomerForwarder.forwarder_id == forwarder_id)
    if deletion_indicator is not None:
        stmt = stmt.where(CustomerForwarder.deletion_indicator == deletion_indicator)
    return list(db.execute(stmt).scalars().all())


def list_customer_forwarders_with_names(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    customer_id: int | None = None,
    forwarder_id: int | None = None,
    deletion_indicator: bool | None = None,
) -> list[CustomerForwarder]:
    stmt = (
        select(CustomerForwarder)
        .options(
            joinedload(CustomerForwarder.customer),
            joinedload(CustomerForwarder.forwarder),
        )
        .offset(skip)
        .limit(limit)
        .order_by(CustomerForwarder.id.desc())
    )
    if customer_id is not None:
        stmt = stmt.where(CustomerForwarder.customer_id == customer_id)
    if forwarder_id is not None:
        stmt = stmt.where(CustomerForwarder.forwarder_id == forwarder_id)
    if deletion_indicator is not None:
        stmt = stmt.where(CustomerForwarder.deletion_indicator == deletion_indicator)
    return list(db.execute(stmt).scalars().all())


def update_customer_forwarder(
    db: Session, row_id: int, data: CustomerForwarderUpdate, current_user_email: str | None = None
) -> CustomerForwarder | None:
    obj = db.get(CustomerForwarder, row_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)
    if current_user_email:
        obj.last_changed_by = current_user_email

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint.") from e

    db.refresh(obj)
    return obj


def delete_customer_forwarder(
    db: Session, row_id: int, mode: str = "soft", current_user_email: str | None = None
) -> bool:
    obj = db.get(CustomerForwarder, row_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.deletion_indicator = True
    if current_user_email:
        obj.last_changed_by = current_user_email
    db.commit()
    return True


def delete_customer_forwarder_by_pair(
    db: Session,
    customer_id: int,
    forwarder_id: int,
    mode: str = "soft",
    current_user_email: str | None = None,
) -> bool:
    obj = get_customer_forwarder_by_pair(db, customer_id, forwarder_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.deletion_indicator = True
    if current_user_email:
        obj.last_changed_by = current_user_email
    db.commit()
    return True


def search_customers(db: Session, query: str) -> list[dict]:
    like = f"%{query}%"
    name_expr = func.coalesce(CustomerMaster.trade_name, CustomerMaster.legal_name)
    stmt = (
        select(CustomerMaster.id, name_expr.label("name"))
        .where(or_(CustomerMaster.legal_name.ilike(like), CustomerMaster.trade_name.ilike(like)))
        .order_by(CustomerMaster.id.desc())
        .limit(10)
    )
    return [{"id": r.id, "name": r.name} for r in db.execute(stmt).all()]


def search_forwarders(db: Session, query: str) -> list[dict]:
    like = f"%{query}%"
    name_expr = func.coalesce(PartnerMaster.trade_name, PartnerMaster.legal_name)
    stmt = (
        select(PartnerMaster.id, name_expr.label("name"))
        .where(or_(PartnerMaster.legal_name.ilike(like), PartnerMaster.trade_name.ilike(like)))
        .order_by(PartnerMaster.id.desc())
        .limit(10)
    )
    return [{"id": r.id, "name": r.name} for r in db.execute(stmt).all()]
