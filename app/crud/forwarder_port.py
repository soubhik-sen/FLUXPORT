from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.forwarder_port import ForwarderPortMap
from app.models.logistics_lookups import PortLookup
from app.schemas.forwarder_port import ForwarderPortCreate, ForwarderPortUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (forwarder_id + port_id)."""


def create_forwarder_port(
    db: Session, data: ForwarderPortCreate, current_user_email: str
) -> ForwarderPortMap:
    existing = get_forwarder_port_by_pair(db, data.forwarder_id, data.port_id)
    if existing:
        if existing.deletion_indicator:
            existing.deletion_indicator = False
            existing.last_changed_by = current_user_email
            db.commit()
            db.refresh(existing)
            return existing
        raise DuplicateError("Forwarder-port map already exists (unique constraint hit).")

    obj = ForwarderPortMap(
        forwarder_id=data.forwarder_id,
        port_id=data.port_id,
        deletion_indicator=data.deletion_indicator,
        created_by=current_user_email,
        last_changed_by=current_user_email,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Forwarder-port map already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_forwarder_port(db: Session, row_id: int) -> ForwarderPortMap | None:
    return db.get(ForwarderPortMap, row_id)


def get_forwarder_port_by_pair(
    db: Session, forwarder_id: int, port_id: int
) -> ForwarderPortMap | None:
    stmt = select(ForwarderPortMap).where(
        ForwarderPortMap.forwarder_id == forwarder_id,
        ForwarderPortMap.port_id == port_id,
    )
    return db.execute(stmt).scalars().first()


def list_forwarder_ports(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    forwarder_id: int | None = None,
    port_id: int | None = None,
    deletion_indicator: bool | None = None,
) -> list[ForwarderPortMap]:
    stmt = select(ForwarderPortMap).offset(skip).limit(limit).order_by(ForwarderPortMap.id.desc())
    if forwarder_id is not None:
        stmt = stmt.where(ForwarderPortMap.forwarder_id == forwarder_id)
    if port_id is not None:
        stmt = stmt.where(ForwarderPortMap.port_id == port_id)
    if deletion_indicator is not None:
        stmt = stmt.where(ForwarderPortMap.deletion_indicator == deletion_indicator)
    return list(db.execute(stmt).scalars().all())


def list_forwarder_ports_with_names(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    forwarder_id: int | None = None,
    port_id: int | None = None,
    deletion_indicator: bool | None = None,
) -> list[ForwarderPortMap]:
    stmt = (
        select(ForwarderPortMap)
        .options(
            joinedload(ForwarderPortMap.forwarder),
            joinedload(ForwarderPortMap.port),
        )
        .offset(skip)
        .limit(limit)
        .order_by(ForwarderPortMap.id.desc())
    )
    if forwarder_id is not None:
        stmt = stmt.where(ForwarderPortMap.forwarder_id == forwarder_id)
    if port_id is not None:
        stmt = stmt.where(ForwarderPortMap.port_id == port_id)
    if deletion_indicator is not None:
        stmt = stmt.where(ForwarderPortMap.deletion_indicator == deletion_indicator)
    return list(db.execute(stmt).scalars().all())


def update_forwarder_port(
    db: Session, row_id: int, data: ForwarderPortUpdate, current_user_email: str | None = None
) -> ForwarderPortMap | None:
    obj = db.get(ForwarderPortMap, row_id)
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


def delete_forwarder_port(
    db: Session, row_id: int, mode: str = "soft", current_user_email: str | None = None
) -> bool:
    obj = db.get(ForwarderPortMap, row_id)
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


def list_ports_for_forwarder(
    db: Session,
    forwarder_id: int,
) -> list[PortLookup]:
    stmt = (
        select(PortLookup)
        .join(ForwarderPortMap, ForwarderPortMap.port_id == PortLookup.id)
        .where(
            ForwarderPortMap.forwarder_id == forwarder_id,
            ForwarderPortMap.deletion_indicator == False,  # noqa: E712
            PortLookup.is_active == True,  # noqa: E712
        )
        .order_by(PortLookup.port_code.asc())
    )
    return list(db.execute(stmt).scalars().all())
