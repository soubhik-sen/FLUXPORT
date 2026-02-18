from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps.request_identity import get_request_email
from app.crud.forwarder_port import (
    count_forwarder_ports,
    DuplicateError,
    create_forwarder_port,
    delete_forwarder_port,
    get_forwarder_port,
    get_forwarder_port_by_pair,
    list_forwarder_ports_with_names,
    update_forwarder_port,
)
from app.db.session import get_db
from app.schemas.forwarder_port import ForwarderPortCreate, ForwarderPortOut, ForwarderPortUpdate

router = APIRouter(prefix="/forwarder-port-map", tags=["forwarder-port-map"])


def _get_user_email(request: Request) -> str:
    return get_request_email(request)


@router.post("", response_model=ForwarderPortOut, status_code=status.HTTP_201_CREATED)
def create_forwarder_port_api(
    payload: ForwarderPortCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        return create_forwarder_port(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/link", response_model=ForwarderPortOut, status_code=status.HTTP_201_CREATED)
def link_forwarder_port_api(
    payload: ForwarderPortCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    existing = get_forwarder_port_by_pair(db, payload.forwarder_id, payload.port_id)
    if existing:
        return existing
    try:
        return create_forwarder_port(db, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=ForwarderPortOut)
def get_forwarder_port_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_forwarder_port(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Forwarder-port map not found")
    return obj


@router.get("", response_model=list[ForwarderPortOut])
def list_forwarder_ports_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    forwarder_id: int | None = Query(None, ge=1),
    port_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_forwarder_ports_with_names(
        db,
        skip=skip,
        limit=limit,
        forwarder_id=forwarder_id,
        port_id=port_id,
        deletion_indicator=deletion_indicator,
    )


@router.get("/paged/list")
def list_forwarder_ports_paged_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    forwarder_id: int | None = Query(None, ge=1),
    port_id: int | None = Query(None, ge=1),
    deletion_indicator: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    items = list_forwarder_ports_with_names(
        db,
        skip=skip,
        limit=limit,
        forwarder_id=forwarder_id,
        port_id=port_id,
        deletion_indicator=deletion_indicator,
    )
    total = count_forwarder_ports(
        db,
        forwarder_id=forwarder_id,
        port_id=port_id,
        deletion_indicator=deletion_indicator,
    )
    return {
        "items": [
            ForwarderPortOut.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.patch("/{row_id}", response_model=ForwarderPortOut)
def update_forwarder_port_api(
    row_id: int,
    payload: ForwarderPortUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    try:
        obj = update_forwarder_port(db, row_id, payload, current_user_email=user_email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Forwarder-port map not found")
    return obj


@router.put("/{row_id}", response_model=ForwarderPortOut)
def update_forwarder_port_put_api(
    row_id: int,
    payload: ForwarderPortUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    return update_forwarder_port_api(row_id, payload, request, db)


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_forwarder_port_api(
    row_id: int,
    request: Request,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    ok = delete_forwarder_port(db, row_id, mode=mode, current_user_email=user_email)
    if not ok:
        raise HTTPException(status_code=404, detail="Forwarder-port map not found")
    return None
