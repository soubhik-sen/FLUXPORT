
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer_branch import CustomerBranch
from app.schemas.customer_branch import CustomerBranchCreate, CustomerBranchUpdate


class DuplicateError(Exception):
    """Raised when a unique constraint is violated (e.g., uq_customer_map)."""


def create_customer_branch(db: Session, data: CustomerBranchCreate) -> CustomerBranch:
    obj = CustomerBranch(
        customer_id=data.customer_id,
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
        raise DuplicateError("Customer branch mapping already exists (unique constraint hit).") from e
    db.refresh(obj)
    return obj


def get_customer_branch(db: Session, row_id: int) -> CustomerBranch | None:
    return db.get(CustomerBranch, row_id)


def list_customer_branches(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    include_deleted: bool = False,
    as_of: date | None = None,
    customer_id: int | None = None,
    branch_id: int | None = None,
) -> list[CustomerBranch]:
    stmt = select(CustomerBranch).offset(skip).limit(limit).order_by(CustomerBranch.id.desc())

    if not include_deleted:
        stmt = stmt.where(CustomerBranch.deletion_indicator.is_(False))

    if customer_id is not None:
        stmt = stmt.where(CustomerBranch.customer_id == customer_id)

    if branch_id is not None:
        stmt = stmt.where(CustomerBranch.branch_id == branch_id)

    if as_of is not None:
        stmt = stmt.where(
            and_(
                or_(CustomerBranch.valid_from.is_(None), CustomerBranch.valid_from <= as_of),
                or_(CustomerBranch.valid_to.is_(None), CustomerBranch.valid_to >= as_of),
            )
        )

    return list(db.execute(stmt).scalars().all())


def update_customer_branch(db: Session, row_id: int, data: CustomerBranchUpdate) -> CustomerBranch | None:
    obj = db.get(CustomerBranch, row_id)
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


def delete_customer_branch(db: Session, row_id: int, mode: str = "soft") -> bool:
    obj = db.get(CustomerBranch, row_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.deletion_indicator = True
    db.commit()
    return True
