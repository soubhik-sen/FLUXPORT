from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.object_types import DuplicateError, create_object_type, delete_object_type, get_object_type, list_object_types, update_object_type
from app.db.session import get_db
from app.schemas.object_types import ObjectTypeCreate, ObjectTypeOut, ObjectTypeUpdate

router = APIRouter(prefix="/object-types", tags=["object-types"])


@router.post("", response_model=ObjectTypeOut, status_code=status.HTTP_201_CREATED)
def create_object_type_api(payload: ObjectTypeCreate, db: Session = Depends(get_db)):
    try:
        return create_object_type(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{object_type}", response_model=ObjectTypeOut)
def get_object_type_api(object_type: str, db: Session = Depends(get_db)):
    obj = get_object_type(db, object_type)
    if not obj:
        raise HTTPException(status_code=404, detail="Object type not found")
    return obj


@router.get("", response_model=list[ObjectTypeOut])
def list_object_types_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    q: str | None = Query(None, description="Search in description"),
    db: Session = Depends(get_db),
):
    return list_object_types(db, skip=skip, limit=limit, q=q)


@router.patch("/{object_type}", response_model=ObjectTypeOut)
def update_object_type_api(object_type: str, payload: ObjectTypeUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_object_type(db, object_type, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Object type not found")
    return obj


@router.delete("/{object_type}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object_type_api(object_type: str, db: Session = Depends(get_db)):
    ok = delete_object_type(db, object_type)
    if not ok:
        raise HTTPException(status_code=404, detail="Object type not found")
    return None
