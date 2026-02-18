from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.user_partner_link import UserPartnerLink
from app.models.users import User
from app.models.partner_master import PartnerMaster
from app.schemas.user_partner_link import UserPartnerLinkCreate, UserPartnerLinkUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (user_email + partner_id)."""


def create_user_partner_link(
    db: Session, data: UserPartnerLinkCreate, current_user_email: str
) -> UserPartnerLink:

    existing = get_user_partner_link_by_pair(db, data.user_email, data.partner_id)
    if existing:
        if getattr(existing, "deletion_indicator", False):
            existing.deletion_indicator = False
            existing.last_changed_by = current_user_email
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        raise DuplicateError("User-partner link already exists (unique constraint hit).")

    obj = UserPartnerLink(
        user_email=data.user_email,
        partner_id=data.partner_id,
        deletion_indicator=data.deletion_indicator,
        created_by=current_user_email,
        last_changed_by=current_user_email,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("User-partner link already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_user_partner_link(db: Session, row_id: int) -> UserPartnerLink | None:
    return db.get(UserPartnerLink, row_id)


def get_user_partner_link_by_pair(
    db: Session, user_email: str, partner_id: int
) -> UserPartnerLink | None:
    stmt = select(UserPartnerLink).where(
        UserPartnerLink.user_email == user_email,
        UserPartnerLink.partner_id == partner_id,
    )
    return db.execute(stmt).scalars().first()


def list_user_partner_links(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_email: str | None = None,
    partner_id: int | None = None,
    deletion_indicator: bool | None = None,
):
    stmt = (
        select(UserPartnerLink)
        .options(joinedload(UserPartnerLink.partner), joinedload(UserPartnerLink.user))
        .offset(skip)
        .limit(limit)
        .order_by(UserPartnerLink.id.desc())
    )
    if user_email is not None:
        stmt = stmt.where(UserPartnerLink.user_email == user_email)
    if partner_id is not None:
        stmt = stmt.where(UserPartnerLink.partner_id == partner_id)
    if deletion_indicator is not None:
        stmt = stmt.where(UserPartnerLink.deletion_indicator == deletion_indicator)
    return list(db.execute(stmt).scalars().all())


def count_user_partner_links(
    db: Session,
    user_email: str | None = None,
    partner_id: int | None = None,
    deletion_indicator: bool | None = None,
) -> int:
    stmt = select(func.count()).select_from(UserPartnerLink)
    if user_email is not None:
        stmt = stmt.where(UserPartnerLink.user_email == user_email)
    if partner_id is not None:
        stmt = stmt.where(UserPartnerLink.partner_id == partner_id)
    if deletion_indicator is not None:
        stmt = stmt.where(UserPartnerLink.deletion_indicator == deletion_indicator)
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


def search_partners(db: Session, query: str) -> list[dict]:
    like = f"%{query}%"
    stmt = (
        select(
            PartnerMaster.id,
            PartnerMaster.legal_name.label("name"),
            PartnerMaster.partner_identifier.label("code"),
        )
        .where(
            or_(
                PartnerMaster.legal_name.ilike(like),
                PartnerMaster.trade_name.ilike(like),
                PartnerMaster.partner_identifier.ilike(like),
            )
        )
        .order_by(PartnerMaster.id.desc())
        .limit(10)
    )
    return [{"id": r.id, "name": r.name, "code": r.code} for r in db.execute(stmt).all()]


def update_user_partner_link(
    db: Session, row_id: int, data: UserPartnerLinkUpdate, current_user_email: str | None = None
) -> UserPartnerLink | None:
    obj = db.get(UserPartnerLink, row_id)
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


def delete_user_partner_link(db: Session, row_id: int, mode: str = "soft", current_user_email: str | None = None) -> bool:
    obj = db.get(UserPartnerLink, row_id)
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
