from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.permissions import (
    DuplicateError,
    create_permission,
    delete_permission,
    get_permission,
    list_permissions,
    update_permission,
)
from app.db.session import get_db
from app.schemas.permissions import PermissionCreate, PermissionOut, PermissionUpdate

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.post("", response_model=PermissionOut, status_code=status.HTTP_201_CREATED)
def create_permission_api(payload: PermissionCreate, db: Session = Depends(get_db)):
    try:
        return create_permission(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{permission_id}", response_model=PermissionOut)
def get_permission_api(permission_id: int, db: Session = Depends(get_db)):
    obj = get_permission(db, permission_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Permission not found")
    return obj


@router.get("", response_model=list[PermissionOut])
def list_permissions_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    action_key: str | None = Query(None),
    object_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_permissions(db, skip=skip, limit=limit, action_key=action_key, object_type=object_type)


@router.patch("/{permission_id}", response_model=PermissionOut)
def update_permission_api(permission_id: int, payload: PermissionUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_permission(db, permission_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Permission not found")
    return obj


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission_api(permission_id: int, db: Session = Depends(get_db)):
    ok = delete_permission(db, permission_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Permission not found")
    return None
