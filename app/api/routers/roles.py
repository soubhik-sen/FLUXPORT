from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.roles import DuplicateError, create_role, delete_role, get_role, list_roles, update_role
from app.db.session import get_db
from app.schemas.roles import RoleCreate, RoleOut, RoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"])


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role_api(payload: RoleCreate, db: Session = Depends(get_db)):
    try:
        return create_role(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{role_id}", response_model=RoleOut)
def get_role_api(role_id: int, db: Session = Depends(get_db)):
    obj = get_role(db, role_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Role not found")
    return obj


@router.get("", response_model=list[RoleOut])
def list_roles_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_roles(db, skip=skip, limit=limit, name=name)


@router.patch("/{role_id}", response_model=RoleOut)
def update_role_api(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_role(db, role_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Role not found")
    return obj


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role_api(role_id: int, db: Session = Depends(get_db)):
    ok = delete_role(db, role_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Role not found")
    return None
