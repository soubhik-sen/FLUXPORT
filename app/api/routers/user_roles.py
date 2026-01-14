from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.user_roles import (
    DuplicateError,
    create_user_role,
    delete_user_role,
    get_user_role,
    list_user_roles,
    update_user_role,
)
from app.db.session import get_db
from app.schemas.user_roles import UserRoleCreate, UserRoleOut, UserRoleUpdate

router = APIRouter(prefix="/user-roles", tags=["user-roles"])


@router.post("", response_model=UserRoleOut, status_code=status.HTTP_201_CREATED)
def create_user_role_api(payload: UserRoleCreate, db: Session = Depends(get_db)):
    try:
        return create_user_role(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=UserRoleOut)
def get_user_role_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_user_role(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User-role mapping not found")
    return obj


@router.get("", response_model=list[UserRoleOut])
def list_user_roles_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_id: int | None = Query(None, ge=1),
    role_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    return list_user_roles(db, skip=skip, limit=limit, user_id=user_id, role_id=role_id)


@router.patch("/{row_id}", response_model=UserRoleOut)
def update_user_role_api(row_id: int, payload: UserRoleUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_user_role(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="User-role mapping not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_role_api(row_id: int, db: Session = Depends(get_db)):
    ok = delete_user_role(db, row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User-role mapping not found")
    return None
