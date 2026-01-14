from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.forwarder import Forwarder
from app.schemas.forwarder import ForwarderCreate, ForwarderUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (e.g., uq_forwarder_map)."""


def create_forwarder(db: Session, data: ForwarderCreate) -> Forwarder:
    obj = Forwarder(
        forwarder_id=data.forwarder_id,
        branch_id=data.branch_id,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        deletion_indicator=data.deletion_indicator,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Forwarder mapping already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_forwarder(db: Session, row_id: int) -> Forwarder | None:
    return db.get(Forwarder, row_id)


def list_forwarders(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    include_deleted: bool = False,
    as_of: date | None = None,
    forwarder_id: int | None = None,
    branch_id: int | None = None,
) -> list[Forwarder]:
    stmt = select(Forwarder).offset(skip).limit(limit).order_by(Forwarder.id.desc())

    if not include_deleted:
        stmt = stmt.where(Forwarder.deletion_indicator.is_(False))

    if forwarder_id is not None:
        stmt = stmt.where(Forwarder.forwarder_id == forwarder_id)

    if branch_id is not None:
        stmt = stmt.where(Forwarder.branch_id == branch_id)

    if as_of is not None:
        stmt = stmt.where(
            and_(
                or_(Forwarder.valid_from.is_(None), Forwarder.valid_from <= as_of),
                or_(Forwarder.valid_to.is_(None), Forwarder.valid_to >= as_of),
            )
        )

    return list(db.execute(stmt).scalars().all())


def update_forwarder(db: Session, row_id: int, data: ForwarderUpdate) -> Forwarder | None:
    obj = db.get(Forwarder, row_id)
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


def delete_forwarder(db: Session, row_id: int, mode: str = "soft") -> bool:
    """
    mode:
      - "soft": sets deletion_indicator=True
      - "hard": deletes the row
    """
    obj = db.get(Forwarder, row_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.deletion_indicator = True
    db.commit()
    return True
