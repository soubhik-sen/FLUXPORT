from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.users import (
    DuplicateError,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)
from app.db.session import get_db
from app.schemas.users import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user_api(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{user_id}", response_model=UserOut)
def get_user_api(user_id: int, db: Session = Depends(get_db)):
    obj = get_user(db, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj


@router.get("", response_model=list[UserOut])
def list_users_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_users(db, skip=skip, limit=limit, is_active=is_active)


@router.patch("/{user_id}", response_model=UserOut)
def update_user_api(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_user(db, user_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_api(
    user_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_user(db, user_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return None
