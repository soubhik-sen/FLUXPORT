from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (e.g., uq_supplier_map)."""


def create_supplier(db: Session, data: SupplierCreate) -> Supplier:
    obj = Supplier(
        supplier_id=data.supplier_id,
        branch_id=data.branch_id,
        addr_id=data.addr_id,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        deletion_indicator=data.deletion_indicator,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Supplier mapping already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_supplier(db: Session, row_id: int) -> Supplier | None:
    return db.get(Supplier, row_id)


def get_suppliers_by_ids(db: Session, row_ids: list[int]) -> list[Supplier]:
    if not row_ids:
        return []
    normalized = sorted(set(row_ids))
    stmt = select(Supplier).where(Supplier.id.in_(normalized))
    return list(db.execute(stmt).scalars().all())


def list_suppliers(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    include_deleted: bool = False,
    as_of: date | None = None,
    supplier_id: int | None = None,
    branch_id: int | None = None,
) -> list[Supplier]:
    stmt = select(Supplier).offset(skip).limit(limit).order_by(Supplier.id.desc())

    if not include_deleted:
        stmt = stmt.where(Supplier.deletion_indicator.is_(False))

    if supplier_id is not None:
        stmt = stmt.where(Supplier.supplier_id == supplier_id)

    if branch_id is not None:
        stmt = stmt.where(Supplier.branch_id == branch_id)

    if as_of is not None:
        stmt = stmt.where(
            and_(
                or_(Supplier.valid_from.is_(None), Supplier.valid_from <= as_of),
                or_(Supplier.valid_to.is_(None), Supplier.valid_to >= as_of),
            )
        )

    return list(db.execute(stmt).scalars().all())


def update_supplier(db: Session, row_id: int, data: SupplierUpdate) -> Supplier | None:
    obj = db.get(Supplier, row_id)
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


def delete_supplier(db: Session, row_id: int, mode: str = "soft") -> bool:
    """
    mode:
      - "soft": sets deletion_indicator=True
      - "hard": deletes the row
    """
    obj = db.get(Supplier, row_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.deletion_indicator = True
    db.commit()
    return True
