from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.user_departments import (
    DuplicateError,
    create_user_department,
    delete_user_department,
    get_user_department,
    list_user_departments,
    update_user_department,
)
from app.db.session import get_db
from app.schemas.user_departments import (
    UserDepartmentCreate,
    UserDepartmentOut,
    UserDepartmentUpdate,
)

router = APIRouter(prefix="/user-departments", tags=["user-departments"])


@router.post("", response_model=UserDepartmentOut, status_code=status.HTTP_201_CREATED)
def create_user_department_api(payload: UserDepartmentCreate, db: Session = Depends(get_db)):
    try:
        return create_user_department(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=UserDepartmentOut)
def get_user_department_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_user_department(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User-department mapping not found")
    return obj


@router.get("", response_model=list[UserDepartmentOut])
def list_user_departments_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_id: int | None = Query(None, ge=1),
    department: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_user_departments(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        department=department,
    )


@router.patch("/{row_id}", response_model=UserDepartmentOut)
def update_user_department_api(row_id: int, payload: UserDepartmentUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_user_department(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="User-department mapping not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_department_api(row_id: int, db: Session = Depends(get_db)):
    ok = delete_user_department(db, row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User-department mapping not found")
    return None
