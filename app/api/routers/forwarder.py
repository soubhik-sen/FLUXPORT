from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.forwarder import (
    DuplicateError,
    create_forwarder,
    delete_forwarder,
    get_forwarder,
    list_forwarders,
    update_forwarder,
)
from app.db.session import get_db
from app.schemas.forwarder import ForwarderCreate, ForwarderOut, ForwarderUpdate

router = APIRouter(prefix="/forwarders", tags=["forwarders"])


@router.post("", response_model=ForwarderOut, status_code=status.HTTP_201_CREATED)
def create_forwarder_api(payload: ForwarderCreate, db: Session = Depends(get_db)):
    try:
        return create_forwarder(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=ForwarderOut)
def get_forwarder_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_forwarder(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Forwarder mapping not found")
    return obj


@router.get("", response_model=list[ForwarderOut])
def list_forwarders_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    include_deleted: bool = Query(False),
    as_of: date | None = Query(None),
    forwarder_id: int | None = Query(None, ge=1),
    branch_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    return list_forwarders(
        db,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        as_of=as_of,
        forwarder_id=forwarder_id,
        branch_id=branch_id,
    )


@router.patch("/{row_id}", response_model=ForwarderOut)
def update_forwarder_api(row_id: int, payload: ForwarderUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_forwarder(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Forwarder mapping not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_forwarder_api(
    row_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_forwarder(db, row_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Forwarder mapping not found")
    return None
