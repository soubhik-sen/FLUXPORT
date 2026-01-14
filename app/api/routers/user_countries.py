from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.user_countries import (
    DuplicateError,
    create_user_country,
    delete_user_country,
    get_user_country,
    list_user_countries,
    update_user_country,
)
from app.db.session import get_db
from app.schemas.user_countries import UserCountryCreate, UserCountryOut, UserCountryUpdate

router = APIRouter(prefix="/user-countries", tags=["user-countries"])


@router.post("", response_model=UserCountryOut, status_code=status.HTTP_201_CREATED)
def create_user_country_api(payload: UserCountryCreate, db: Session = Depends(get_db)):
    try:
        return create_user_country(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=UserCountryOut)
def get_user_country_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_user_country(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User-country mapping not found")
    return obj


@router.get("", response_model=list[UserCountryOut])
def list_user_countries_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_id: int | None = Query(None, ge=1),
    country_code: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_user_countries(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        country_code=country_code,
    )


@router.patch("/{row_id}", response_model=UserCountryOut)
def update_user_country_api(row_id: int, payload: UserCountryUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_user_country(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="User-country mapping not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_country_api(row_id: int, db: Session = Depends(get_db)):
    ok = delete_user_country(db, row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User-country mapping not found")
    return None
