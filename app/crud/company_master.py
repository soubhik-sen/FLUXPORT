from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company_master import CompanyMaster
from app.schemas.company_master import CompanyMasterCreate, CompanyMasterUpdate
from app.services.number_range_get import NumberRangeService


class DuplicateError(Exception):
    """Raised when a unique constraint is violated."""


def _resolve_company_code(db: Session, requested_code: str | None) -> str:
    candidate = (requested_code or "").strip()
    if candidate:
        return candidate
    try:
        return NumberRangeService.get_next_number(db, "COMPANY", 1)
    except ValueError as exc:
        raise ValueError(
            "No active number range found for COMPANY with type 1. "
            "Configure sys-number-ranges first."
        ) from exc


def create_company_master(db: Session, data: CompanyMasterCreate) -> CompanyMaster:
    company_code = _resolve_company_code(db, data.company_code)
    obj = CompanyMaster(
        company_code=company_code,
        branch_code=data.branch_code,
        legal_name=data.legal_name,
        trade_name=data.trade_name,
        tax_id=data.tax_id,
        is_active=data.is_active,
        addr_id=data.addr_id,
        default_currency=data.default_currency,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateError("Company already exists (unique constraint hit).") from exc
    db.refresh(obj)
    return obj


def get_company_master(db: Session, company_id: int) -> CompanyMaster | None:
    return db.get(CompanyMaster, company_id)


def list_company_master(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
    q: str | None = None,
) -> list[CompanyMaster]:
    stmt = select(CompanyMaster).offset(skip).limit(limit).order_by(CompanyMaster.id.desc())
    if is_active is not None:
        stmt = stmt.where(CompanyMaster.is_active == is_active)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                CompanyMaster.company_code.ilike(like),
                CompanyMaster.branch_code.ilike(like),
                CompanyMaster.legal_name.ilike(like),
                CompanyMaster.trade_name.ilike(like),
            )
        )
    return list(db.execute(stmt).scalars().all())


def update_company_master(
    db: Session,
    company_id: int,
    data: CompanyMasterUpdate,
) -> CompanyMaster | None:
    obj = db.get(CompanyMaster, company_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for key, value in patch.items():
        setattr(obj, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateError("Update violates unique constraint.") from exc

    db.refresh(obj)
    return obj


def delete_company_master(db: Session, company_id: int, mode: str = "soft") -> bool:
    obj = db.get(CompanyMaster, company_id)
    if not obj:
        return False

    if mode == "hard":
        db.delete(obj)
        db.commit()
        return True

    obj.is_active = False
    db.commit()
    return True
