from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.user_attributes import (
    DuplicateError,
    create_user_attribute,
    delete_user_attribute,
    get_user_attribute,
    list_user_attributes,
    update_user_attribute,
)
from app.db.session import get_db
from app.schemas.user_attributes import (
    UserAttributeCreate,
    UserAttributeOut,
    UserAttributeUpdate,
)

router = APIRouter(prefix="/user-attributes", tags=["user-attributes"])


@router.post("", response_model=UserAttributeOut, status_code=status.HTTP_201_CREATED)
def create_user_attribute_api(payload: UserAttributeCreate, db: Session = Depends(get_db)):
    try:
        return create_user_attribute(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=UserAttributeOut)
def get_user_attribute_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_user_attribute(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User-attribute not found")
    return obj


@router.get("", response_model=list[UserAttributeOut])
def list_user_attributes_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_id: int | None = Query(None, ge=1),
    key: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_user_attributes(db, skip=skip, limit=limit, user_id=user_id, key=key)


@router.patch("/{row_id}", response_model=UserAttributeOut)
def update_user_attribute_api(row_id: int, payload: UserAttributeUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_user_attribute(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="User-attribute not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_attribute_api(row_id: int, db: Session = Depends(get_db)):
    ok = delete_user_attribute(db, row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User-attribute not found")
    return None
