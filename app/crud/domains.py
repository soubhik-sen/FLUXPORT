from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.domains import Domain
from app.schemas.domains import DomainCreate, DomainUpdate


class DuplicateError(Exception):
    """Raised when unique constraint is violated (uq_domains_name_key)."""


def create_domain(db: Session, data: DomainCreate) -> Domain:
    obj = Domain(
        domain_name=data.domain_name,
        technical_key=data.technical_key,
        display_label=data.display_label,
        is_active=data.is_active,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Domain entry already exists (domain_name + technical_key must be unique).") from e
    db.refresh(obj)
    return obj


def get_domain(db: Session, domain_id: int) -> Domain | None:
    return db.get(Domain, domain_id)


def list_domains(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    domain_name: str | None = None,
    technical_key: str | None = None,
    is_active: bool | None = None,
) -> list[Domain]:
    stmt = select(Domain).offset(skip).limit(limit).order_by(Domain.id.desc())

    if domain_name is not None:
        stmt = stmt.where(Domain.domain_name == domain_name)
    if technical_key is not None:
        stmt = stmt.where(Domain.technical_key == technical_key)
    if is_active is not None:
        stmt = stmt.where(Domain.is_active == is_active)

    return list(db.execute(stmt).scalars().all())


def update_domain(db: Session, domain_id: int, data: DomainUpdate) -> Domain | None:
    obj = db.get(Domain, domain_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (domain_name + technical_key).") from e

    db.refresh(obj)
    return obj


def delete_domain(db: Session, domain_id: int) -> bool:
    obj = db.get(Domain, domain_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
