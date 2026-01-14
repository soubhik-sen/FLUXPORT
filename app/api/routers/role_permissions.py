from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.role_permissions import (
    DuplicateError,
    create_role_permission,
    delete_role_permission,
    get_role_permission,
    list_role_permissions,
    update_role_permission,
)
from app.db.session import get_db
from app.schemas.role_permissions import (
    RolePermissionCreate,
    RolePermissionOut,
    RolePermissionUpdate,
)

router = APIRouter(prefix="/role-permissions", tags=["role-permissions"])


@router.post("", response_model=RolePermissionOut, status_code=status.HTTP_201_CREATED)
def create_role_permission_api(payload: RolePermissionCreate, db: Session = Depends(get_db)):
    try:
        return create_role_permission(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=RolePermissionOut)
def get_role_permission_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_role_permission(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Role-permission mapping not found")
    return obj


@router.get("", response_model=list[RolePermissionOut])
def list_role_permissions_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    role_id: int | None = Query(None, ge=1),
    permission_id: int | None = Query(None, ge=1),
    role_name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_role_permissions(
        db,
        skip=skip,
        limit=limit,
        role_id=role_id,
        permission_id=permission_id,
        role_name=role_name,
    )


@router.patch("/{row_id}", response_model=RolePermissionOut)
def update_role_permission_api(row_id: int, payload: RolePermissionUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_role_permission(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Role-permission mapping not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role_permission_api(row_id: int, db: Session = Depends(get_db)):
    ok = delete_role_permission(db, row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Role-permission mapping not found")
    return None
