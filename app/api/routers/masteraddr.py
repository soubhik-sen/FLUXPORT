from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.crud.masteraddr import (
    DuplicateError,
    create_masteraddr,
    delete_masteraddr,
    get_masteraddr,
    list_masteraddr,
    update_masteraddr,
)
from app.db.session import get_db
from app.schemas.masteraddr import MasterAddrCreate, MasterAddrOut, MasterAddrUpdate

router = APIRouter(prefix="/masteraddr", tags=["masteraddr"])


def _get_user_email(request: Request) -> str:
    return request.headers.get("X-User-Email") or request.headers.get("X-User") or "system@local"


@router.post("", response_model=MasterAddrOut, status_code=status.HTTP_201_CREATED)
def create_masteraddr_api(
    payload: MasterAddrCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        return create_masteraddr(db, payload, current_user_email=_get_user_email(request))
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{addr_id}", response_model=MasterAddrOut)
def get_masteraddr_api(addr_id: int, db: Session = Depends(get_db)):
    obj = get_masteraddr(db, addr_id)
    if not obj:
        raise HTTPException(status_code=404, detail="MasterAddr not found")
    return obj


@router.get("", response_model=list[MasterAddrOut])
def list_masteraddr_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    include_deleted: bool = Query(False),
    as_of: date | None = Query(None, description="Return records valid on this date"),
    name: str | None = Query(None, description="Case-insensitive contains filter"),
    addr_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_masteraddr(
        db,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        as_of=as_of,
        name=name,
        addr_type=addr_type,
    )


@router.patch("/{addr_id}", response_model=MasterAddrOut)
def update_masteraddr_api(
    addr_id: int,
    payload: MasterAddrUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        obj = update_masteraddr(db, addr_id, payload, current_user_email=_get_user_email(request))
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="MasterAddr not found")
    return obj


@router.delete("/{addr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_masteraddr_api(
    addr_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_masteraddr(db, addr_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="MasterAddr not found")
    return None
