from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_departments import UserDepartment
from app.schemas.user_departments import UserDepartmentCreate, UserDepartmentUpdate


class DuplicateError(Exception):
    """Raised when unique constraint is violated (uq_user_departments_user_dept)."""


def create_user_department(db: Session, data: UserDepartmentCreate) -> UserDepartment:
    obj = UserDepartment(user_id=data.user_id, department=data.department)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Mapping already exists (user_id + department must be unique).") from e
    db.refresh(obj)
    return obj


def get_user_department(db: Session, row_id: int) -> UserDepartment | None:
    return db.get(UserDepartment, row_id)


def list_user_departments(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = None,
    department: str | None = None,
) -> list[UserDepartment]:
    stmt = select(UserDepartment).offset(skip).limit(limit).order_by(UserDepartment.id.desc())

    if user_id is not None:
        stmt = stmt.where(UserDepartment.user_id == user_id)
    if department is not None:
        stmt = stmt.where(UserDepartment.department.ilike(f"%{department}%"))

    return list(db.execute(stmt).scalars().all())


def update_user_department(db: Session, row_id: int, data: UserDepartmentUpdate) -> UserDepartment | None:
    obj = db.get(UserDepartment, row_id)
    if not obj:
        return None

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError("Update violates unique constraint (user_id + department).") from e

    db.refresh(obj)
    return obj


def delete_user_department(db: Session, row_id: int) -> bool:
    obj = db.get(UserDepartment, row_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
