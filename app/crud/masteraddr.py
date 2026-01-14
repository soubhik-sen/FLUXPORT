from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.masteraddr import MasterAddr
from app.schemas.masteraddr import MasterAddrCreate, MasterAddrUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (e.g., uq_masteraddr_name_type)."""


def create_masteraddr(db: Session, data: MasterAddrCreate) -> MasterAddr:
    obj = MasterAddr(
        name=data.name,
        addr_type=data.addr_type,
        country=data.country,
        region=data.region,
        city=data.city,
        zip=data.zip,
        street=data.street,
        housenumber=data.housenumber,
        phone1=data.phone1,
        phone2=data.phone2,
        emailid=str(data.emailid) if data.emailid is not None else None,
        timezone=data.timezone,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        deletion_indicator=data.deletion_indicator,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("MasterAddr already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_masteraddr(db: Session, addr_id: int) -> MasterAddr | None:
    return db.get(MasterAddr, addr_id)


def list_masteraddr(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    include_deleted: bool = False,
    as_of: date | None = None,
    name: str | None = None,
    addr_type: str | None = None,
) -> list[MasterAddr]:
    stmt = select(MasterAddr).offset(skip).limit(limit).order_by(MasterAddr.id.desc())

    if not include_deleted:
        stmt = stmt.where(MasterAddr.deletion_indicator.is_(False))

    if name:
        stmt = stmt.where(MasterAddr.name.ilike(f"%{name}%"))

    if addr_type:
        stmt = stmt.where(MasterAddr.addr_type == addr_type)

    # validity filter: record is active on as_of date
    if as_of is not None:
        stmt = stmt.where(
            and_(
                or_(MasterAddr.valid_from.is_(None), MasterAddr.valid_from <= as_of),
                or_(MasterAddr.valid_to.is_(None), MasterAddr.valid_to >= as_of),
            )
        )

    return list(db.execute(stmt).scalars().all())


def update_masteraddr(db: Session, addr_id: int, data: MasterAddrUpdate) -> MasterAddr | None:
    obj = db.get(MasterAddr, addr_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        if k == "emailid" and v is not None:
            v = str(v)
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint.") from e

    db.refresh(obj)
    return obj


def delete_masteraddr(db: Session, addr_id: int, mode: str = "soft") -> bool:
    """
    mode:
      - "soft": sets deletion_indicator=True
      - "hard": deletes the row
    """
    obj = db.get(MasterAddr, addr_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.deletion_indicator = True
    db.commit()
    return True
