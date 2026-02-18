from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.user_customer_link import UserCustomerLink
from app.models.users import User
from app.models.customer_master import CustomerMaster
from app.schemas.user_customer_link import UserCustomerLinkCreate, UserCustomerLinkUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (user_email + customer_id)."""


def create_user_customer_link(
    db: Session, data: UserCustomerLinkCreate, current_user_email: str
) -> UserCustomerLink:

    existing = get_user_customer_link_by_pair(db, data.user_email, data.customer_id)
    if existing:
        if getattr(existing, "deletion_indicator", False):
            existing.deletion_indicator = False
            existing.last_changed_by = current_user_email
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        raise DuplicateError("User-customer link already exists (unique constraint hit).")

    obj = UserCustomerLink(
        user_email=data.user_email,
        customer_id=data.customer_id,
        deletion_indicator=data.deletion_indicator,
        created_by=current_user_email,
        last_changed_by=current_user_email,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("User-customer link already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_user_customer_link(db: Session, row_id: int) -> UserCustomerLink | None:
    return db.get(UserCustomerLink, row_id)


def get_user_customer_link_by_pair(
    db: Session, user_email: str, customer_id: int
) -> UserCustomerLink | None:
    stmt = select(UserCustomerLink).where(
        UserCustomerLink.user_email == user_email,
        UserCustomerLink.customer_id == customer_id,
    )
    return db.execute(stmt).scalars().first()


def list_user_customer_links(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_email: str | None = None,
    customer_id: int | None = None,
    deletion_indicator: bool | None = None,
) -> list[UserCustomerLink]:
    stmt = (
        select(UserCustomerLink)
        .options(
            joinedload(UserCustomerLink.customer).joinedload(CustomerMaster.company),
            joinedload(UserCustomerLink.user),
        )
        .offset(skip)
        .limit(limit)
        .order_by(UserCustomerLink.id.desc())
    )
    if user_email is not None:
        stmt = stmt.where(UserCustomerLink.user_email == user_email)
    if customer_id is not None:
        stmt = stmt.where(UserCustomerLink.customer_id == customer_id)
    if deletion_indicator is not None:
        stmt = stmt.where(UserCustomerLink.deletion_indicator == deletion_indicator)
    return list(db.execute(stmt).scalars().all())


def count_user_customer_links(
    db: Session,
    user_email: str | None = None,
    customer_id: int | None = None,
    deletion_indicator: bool | None = None,
) -> int:
    stmt = select(func.count()).select_from(UserCustomerLink)
    if user_email is not None:
        stmt = stmt.where(UserCustomerLink.user_email == user_email)
    if customer_id is not None:
        stmt = stmt.where(UserCustomerLink.customer_id == customer_id)
    if deletion_indicator is not None:
        stmt = stmt.where(UserCustomerLink.deletion_indicator == deletion_indicator)
    return int(db.execute(stmt).scalar_one())


def search_users(db: Session, query: str) -> list[dict]:
    like = f"%{query}%"
    stmt = (
        select(User.id, User.email, User.username)
        .where(or_(User.email.ilike(like), User.username.ilike(like)))
        .order_by(User.id.desc())
        .limit(10)
    )
    return [
        {"id": r.id, "email": r.email, "name": r.username or r.email}
        for r in db.execute(stmt).all()
    ]


def search_customers(db: Session, query: str) -> list[dict]:
    like = f"%{query}%"
    name_expr = func.coalesce(CustomerMaster.trade_name, CustomerMaster.legal_name)
    stmt = (
        select(
            CustomerMaster.id,
            name_expr.label("name"),
            CustomerMaster.customer_identifier.label("code"),
        )
        .where(
            or_(
                CustomerMaster.legal_name.ilike(like),
                CustomerMaster.trade_name.ilike(like),
                CustomerMaster.customer_identifier.ilike(like),
            )
        )
        .order_by(CustomerMaster.id.desc())
        .limit(10)
    )
    return [{"id": r.id, "name": r.name, "code": r.code} for r in db.execute(stmt).all()]


def update_user_customer_link(
    db: Session, row_id: int, data: UserCustomerLinkUpdate, current_user_email: str | None = None
) -> UserCustomerLink | None:
    obj = db.get(UserCustomerLink, row_id)
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


def delete_user_customer_link(db: Session, row_id: int, mode: str = "soft", current_user_email: str | None = None) -> bool:
    obj = db.get(UserCustomerLink, row_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.deletion_indicator = True
    if current_user_email:
        obj.last_changed_by = current_user_email
    obj.updated_at = datetime.utcnow()
    db.commit()
    return True
