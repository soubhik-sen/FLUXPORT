from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps.request_identity import get_request_email
from app.crud.event_profile import (
    ConcurrencyError,
    DuplicateError,
    DependencyError,
    create_event_instance,
    create_event_profile,
    create_profile_event_map,
    delete_event_instance,
    delete_event_profile,
    delete_profile_event_map,
    get_event_instance,
    get_event_profile,
    get_profile_event_map,
    list_event_instances,
    list_event_profiles,
    list_profile_event_maps,
    update_event_instance,
    update_event_profile,
    update_profile_event_map,
)
from app.db.session import get_db
from app.schemas.event_profile import (
    EventInstanceCreate,
    EventInstanceOut,
    EventInstanceUpdate,
    EventProfileCreate,
    EventProfileOut,
    EventProfileUpdate,
    ProfileEventMapCreate,
    ProfileEventMapOut,
    ProfileEventMapUpdate,
)

router = APIRouter(tags=["event-maintenance"])


def _get_user_email(request: Request) -> str:
    return get_request_email(request)


def _profile_event_map_to_out(row) -> ProfileEventMapOut:
    return ProfileEventMapOut(
        id=row.id,
        profile_id=row.profile_id,
        event_code=row.event_code,
        inclusion_rule_id=row.inclusion_rule_id,
        anchor_event_code=row.anchor_event_code,
        sequence=row.sequence,
        offset_days=row.offset_days,
        is_mandatory=row.is_mandatory,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        last_changed_by=row.last_changed_by,
        profile_name=row.profile.name if row.profile else None,
        event_name=row.event.event_name if row.event else None,
        anchor_event_name=row.anchor_event.event_name if row.anchor_event else None,
    )


def _event_instance_to_out(row) -> EventInstanceOut:
    return EventInstanceOut(
        id=row.id,
        parent_id=row.parent_id,
        po_header_id=row.po_header_id,
        shipment_header_id=row.shipment_header_id,
        po_number=row.po_number,
        shipment_number=row.shipment_number,
        profile_id=row.profile_id,
        profile_version=row.profile_version,
        event_code=row.event_code,
        baseline_date=row.baseline_date,
        planned_date=row.planned_date,
        planned_date_manual_override=row.planned_date_manual_override,
        status_reason=row.status_reason,
        timezone=row.timezone,
        actual_date=row.actual_date,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        last_changed_by=row.last_changed_by,
        event_name=row.event.event_name if row.event else None,
    )


@router.post("/event_profile", response_model=EventProfileOut, status_code=status.HTTP_201_CREATED)
def create_event_profile_api(
    payload: EventProfileCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        return create_event_profile(db, payload, current_user_email=user_email)
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/event_profile/{profile_id}", response_model=EventProfileOut)
def get_event_profile_api(profile_id: int, db: Session = Depends(get_db)):
    row = get_event_profile(db, profile_id)
    if not row:
        raise HTTPException(status_code=404, detail="Event profile not found")
    return row


@router.get("/event_profile", response_model=list[EventProfileOut])
def list_event_profile_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_event_profiles(db, skip=skip, limit=limit, name=name)


@router.patch("/event_profile/{profile_id}", response_model=EventProfileOut)
def update_event_profile_api(
    profile_id: int, payload: EventProfileUpdate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        row = update_event_profile(db, profile_id, payload, current_user_email=user_email)
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not row:
        raise HTTPException(status_code=404, detail="Event profile not found")
    return row


@router.put("/event_profile/{profile_id}", response_model=EventProfileOut)
def put_event_profile_api(
    profile_id: int, payload: EventProfileUpdate, request: Request, db: Session = Depends(get_db)
):
    return update_event_profile_api(profile_id, payload, request, db)


@router.delete("/event_profile/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_profile_api(profile_id: int, db: Session = Depends(get_db)):
    ok = delete_event_profile(db, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event profile not found")
    return None


@router.post("/profile_event_map", response_model=ProfileEventMapOut, status_code=status.HTTP_201_CREATED)
def create_profile_event_map_api(
    payload: ProfileEventMapCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        row = create_profile_event_map(db, payload, current_user_email=user_email)
        row = get_profile_event_map(db, row.id)
        return _profile_event_map_to_out(row)
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DependencyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=str(exc.orig))


@router.get("/profile_event_map/{row_id}", response_model=ProfileEventMapOut)
def get_profile_event_map_api(row_id: int, db: Session = Depends(get_db)):
    row = get_profile_event_map(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Profile-event map not found")
    return _profile_event_map_to_out(row)


@router.get("/profile_event_map", response_model=list[ProfileEventMapOut])
def list_profile_event_map_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    profile_id: int | None = Query(None, ge=1),
    event_code: str | None = Query(None),
    db: Session = Depends(get_db),
):
    rows = list_profile_event_maps(
        db,
        skip=skip,
        limit=limit,
        profile_id=profile_id,
        event_code=event_code,
    )
    return [_profile_event_map_to_out(row) for row in rows]


@router.patch("/profile_event_map/{row_id}", response_model=ProfileEventMapOut)
def update_profile_event_map_api(
    row_id: int, payload: ProfileEventMapUpdate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        row = update_profile_event_map(db, row_id, payload, current_user_email=user_email)
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DependencyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=str(exc.orig))
    if not row:
        raise HTTPException(status_code=404, detail="Profile-event map not found")
    return _profile_event_map_to_out(row)


@router.put("/profile_event_map/{row_id}", response_model=ProfileEventMapOut)
def put_profile_event_map_api(
    row_id: int, payload: ProfileEventMapUpdate, request: Request, db: Session = Depends(get_db)
):
    return update_profile_event_map_api(row_id, payload, request, db)


@router.delete("/profile_event_map/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile_event_map_api(row_id: int, db: Session = Depends(get_db)):
    ok = delete_profile_event_map(db, row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile-event map not found")
    return None


@router.post("/event_instance", response_model=EventInstanceOut, status_code=status.HTTP_201_CREATED)
def create_event_instance_api(
    payload: EventInstanceCreate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        row = create_event_instance(db, payload, current_user_email=user_email)
        row = get_event_instance(db, row.id)
        return _event_instance_to_out(row)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=str(exc.orig))
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/event_instance/{row_id}", response_model=EventInstanceOut)
def get_event_instance_api(row_id: int, db: Session = Depends(get_db)):
    row = get_event_instance(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Event instance not found")
    return _event_instance_to_out(row)


@router.get("/event_instance", response_model=list[EventInstanceOut])
def list_event_instance_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    parent_id: int | None = Query(None, ge=1),
    event_code: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    rows = list_event_instances(
        db,
        skip=skip,
        limit=limit,
        parent_id=parent_id,
        event_code=event_code,
        status=status_filter,
    )
    return [_event_instance_to_out(row) for row in rows]


@router.patch("/event_instance/{row_id}", response_model=EventInstanceOut)
def update_event_instance_api(
    row_id: int, payload: EventInstanceUpdate, request: Request, db: Session = Depends(get_db)
):
    user_email = _get_user_email(request)
    try:
        row = update_event_instance(db, row_id, payload, current_user_email=user_email)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=str(exc.orig))
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not row:
        raise HTTPException(status_code=404, detail="Event instance not found")
    return _event_instance_to_out(row)


@router.put("/event_instance/{row_id}", response_model=EventInstanceOut)
def put_event_instance_api(
    row_id: int, payload: EventInstanceUpdate, request: Request, db: Session = Depends(get_db)
):
    return update_event_instance_api(row_id, payload, request, db)


@router.delete("/event_instance/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_instance_api(row_id: int, db: Session = Depends(get_db)):
    ok = delete_event_instance(db, row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event instance not found")
    return None
