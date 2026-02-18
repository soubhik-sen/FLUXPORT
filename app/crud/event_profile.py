from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.event_profile import EventInstance, EventProfile, ProfileEventMap
from app.models.purchase_order import PurchaseOrderHeader
from app.models.shipment import ShipmentHeader
from app.schemas.event_profile import (
    EventInstanceCreate,
    EventInstanceUpdate,
    EventProfileCreate,
    EventProfileUpdate,
    ProfileEventMapCreate,
    ProfileEventMapUpdate,
)


class DuplicateError(Exception):
    pass


class DependencyError(Exception):
    pass


class ConcurrencyError(Exception):
    pass


def _resolve_parent_numbers(
    db: Session,
    po_header_id: int | None,
    shipment_header_id: int | None,
) -> tuple[str | None, str | None]:
    po_number = None
    shipment_number = None
    if po_header_id is not None:
        row = (
            db.query(PurchaseOrderHeader.po_number)
            .filter(PurchaseOrderHeader.id == po_header_id)
            .first()
        )
        if row and row[0]:
            po_number = str(row[0])
    if shipment_header_id is not None:
        row = (
            db.query(ShipmentHeader.shipment_number)
            .filter(ShipmentHeader.id == shipment_header_id)
            .first()
        )
        if row and row[0]:
            shipment_number = str(row[0])
    return po_number, shipment_number


def _validate_profile_window(effective_from, effective_to) -> None:
    if effective_from and effective_to and effective_from > effective_to:
        raise ValueError("effective_from cannot be after effective_to.")


def _validate_profile_dependencies(
    db: Session,
    profile_id: int,
    event_code: str,
    anchor_event_code: str | None,
    exclude_id: int | None = None,
) -> None:
    if anchor_event_code and anchor_event_code == event_code:
        raise DependencyError("anchor_event_code cannot match event_code.")

    rows = (
        db.query(ProfileEventMap)
        .filter(ProfileEventMap.profile_id == profile_id)
        .all()
    )
    edges: dict[str, str | None] = {}
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        edges[row.event_code] = row.anchor_event_code

    edges[event_code] = anchor_event_code

    if anchor_event_code and anchor_event_code not in edges:
        raise DependencyError("anchor_event_code must reference an event in the same profile.")

    visited: set[str] = set()
    for node in edges.keys():
        if node in visited:
            continue
        trail: set[str] = set()
        current = node
        while current:
            if current in trail:
                raise DependencyError("Cyclic dependency detected in profile events.")
            trail.add(current)
            next_node = edges.get(current)
            if next_node is None:
                break
            current = next_node
        visited.update(trail)


def create_event_profile(db: Session, data: EventProfileCreate, current_user_email: str) -> EventProfile:
    _validate_profile_window(data.effective_from, data.effective_to)
    obj = EventProfile(
        name=data.name,
        description=data.description,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        timezone=data.timezone,
        created_by=current_user_email,
        last_changed_by=current_user_email,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateError("Event profile already exists.") from exc
    db.refresh(obj)
    return obj


def get_event_profile(db: Session, profile_id: int) -> EventProfile | None:
    return db.get(EventProfile, profile_id)


def list_event_profiles(
    db: Session, skip: int = 0, limit: int = 50, name: str | None = None
) -> list[EventProfile]:
    stmt = select(EventProfile).offset(skip).limit(limit).order_by(EventProfile.id.desc())
    if name:
        stmt = stmt.where(EventProfile.name.ilike(f"%{name}%"))
    return list(db.execute(stmt).scalars().all())


def update_event_profile(
    db: Session, profile_id: int, data: EventProfileUpdate, current_user_email: str
) -> EventProfile | None:
    obj = db.get(EventProfile, profile_id)
    if not obj:
        return None
    patch = data.model_dump(exclude_unset=True)
    effective_from = patch.get("effective_from", obj.effective_from)
    effective_to = patch.get("effective_to", obj.effective_to)
    _validate_profile_window(effective_from, effective_to)
    for key, value in patch.items():
        setattr(obj, key, value)
    if patch:
        obj.profile_version = (obj.profile_version or 1) + 1
    obj.last_changed_by = current_user_email
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateError("Update violates unique constraint.") from exc
    except StaleDataError as exc:
        db.rollback()
        raise ConcurrencyError("Event profile was updated by another transaction.") from exc
    db.refresh(obj)
    return obj


def delete_event_profile(db: Session, profile_id: int) -> bool:
    obj = db.get(EventProfile, profile_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


def create_profile_event_map(
    db: Session, data: ProfileEventMapCreate, current_user_email: str
) -> ProfileEventMap:
    _validate_profile_dependencies(
        db,
        profile_id=data.profile_id,
        event_code=data.event_code,
        anchor_event_code=data.anchor_event_code,
    )
    profile = db.get(EventProfile, data.profile_id)
    if profile is not None:
        profile.profile_version = (profile.profile_version or 1) + 1
    obj = ProfileEventMap(
        profile_id=data.profile_id,
        event_code=data.event_code,
        inclusion_rule_id=data.inclusion_rule_id,
        anchor_event_code=data.anchor_event_code,
        sequence=data.sequence,
        offset_days=data.offset_days,
        is_mandatory=data.is_mandatory,
        created_by=current_user_email,
        last_changed_by=current_user_email,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateError("Profile-event mapping already exists.") from exc
    except StaleDataError as exc:
        db.rollback()
        raise ConcurrencyError("Profile-event mapping was updated by another transaction.") from exc
    db.refresh(obj)
    return obj


def get_profile_event_map(db: Session, row_id: int) -> ProfileEventMap | None:
    return (
        db.query(ProfileEventMap)
        .options(
            joinedload(ProfileEventMap.profile),
            joinedload(ProfileEventMap.event),
            joinedload(ProfileEventMap.anchor_event),
        )
        .filter(ProfileEventMap.id == row_id)
        .first()
    )


def list_profile_event_maps(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    profile_id: int | None = None,
    event_code: str | None = None,
) -> list[ProfileEventMap]:
    stmt = (
        select(ProfileEventMap)
        .options(
            joinedload(ProfileEventMap.profile),
            joinedload(ProfileEventMap.event),
            joinedload(ProfileEventMap.anchor_event),
        )
        .offset(skip)
        .limit(limit)
        .order_by(ProfileEventMap.id.desc())
    )
    if profile_id is not None:
        stmt = stmt.where(ProfileEventMap.profile_id == profile_id)
    if event_code:
        stmt = stmt.where(ProfileEventMap.event_code == event_code)
    return list(db.execute(stmt).scalars().all())


def update_profile_event_map(
    db: Session, row_id: int, data: ProfileEventMapUpdate, current_user_email: str
) -> ProfileEventMap | None:
    obj = db.get(ProfileEventMap, row_id)
    if not obj:
        return None
    patch = data.model_dump(exclude_unset=True)
    next_profile_id = patch.get("profile_id", obj.profile_id)
    next_event_code = patch.get("event_code", obj.event_code)
    next_anchor = patch.get("anchor_event_code", obj.anchor_event_code)
    _validate_profile_dependencies(
        db,
        profile_id=next_profile_id,
        event_code=next_event_code,
        anchor_event_code=next_anchor,
        exclude_id=obj.id,
    )
    for key, value in patch.items():
        setattr(obj, key, value)
    obj.last_changed_by = current_user_email
    profile = db.get(EventProfile, obj.profile_id)
    if profile is not None:
        profile.profile_version = (profile.profile_version or 1) + 1
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateError("Update violates unique constraint.") from exc
    except StaleDataError as exc:
        db.rollback()
        raise ConcurrencyError("Profile-event mapping was updated by another transaction.") from exc
    db.refresh(obj)
    return get_profile_event_map(db, obj.id)


def delete_profile_event_map(db: Session, row_id: int) -> bool:
    obj = db.get(ProfileEventMap, row_id)
    if not obj:
        return False
    profile = db.get(EventProfile, obj.profile_id)
    if profile is not None:
        profile.profile_version = (profile.profile_version or 1) + 1
    db.delete(obj)
    db.commit()
    return True


def create_event_instance(
    db: Session, data: EventInstanceCreate, current_user_email: str
) -> EventInstance:
    po_number, shipment_number = _resolve_parent_numbers(
        db=db,
        po_header_id=data.po_header_id,
        shipment_header_id=data.shipment_header_id,
    )
    obj = EventInstance(
        parent_id=data.parent_id,
        po_header_id=data.po_header_id,
        shipment_header_id=data.shipment_header_id,
        po_number=data.po_number or po_number,
        shipment_number=data.shipment_number or shipment_number,
        profile_id=data.profile_id,
        profile_version=data.profile_version,
        event_code=data.event_code,
        baseline_date=data.baseline_date,
        planned_date=data.planned_date,
        planned_date_manual_override=data.planned_date_manual_override,
        status_reason=data.status_reason,
        timezone=data.timezone or "UTC",
        actual_date=data.actual_date,
        status=data.status,
        created_by=current_user_email,
        last_changed_by=current_user_email,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_event_instance(db: Session, row_id: int) -> EventInstance | None:
    return (
        db.query(EventInstance)
        .options(joinedload(EventInstance.event))
        .filter(EventInstance.id == row_id)
        .first()
    )


def list_event_instances(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    parent_id: int | None = None,
    event_code: str | None = None,
    status: str | None = None,
) -> list[EventInstance]:
    stmt = (
        select(EventInstance)
        .options(joinedload(EventInstance.event))
        .offset(skip)
        .limit(limit)
        .order_by(EventInstance.id.desc())
    )
    if parent_id is not None:
        stmt = stmt.where(EventInstance.parent_id == parent_id)
    if event_code:
        stmt = stmt.where(EventInstance.event_code == event_code)
    if status:
        stmt = stmt.where(EventInstance.status == status)
    return list(db.execute(stmt).scalars().all())


def update_event_instance(
    db: Session, row_id: int, data: EventInstanceUpdate, current_user_email: str
) -> EventInstance | None:
    obj = db.get(EventInstance, row_id)
    if not obj:
        return None
    patch = data.model_dump(exclude_unset=True)
    if "planned_date" in patch and "planned_date_manual_override" not in patch:
        if patch["planned_date"] != obj.planned_date:
            patch["planned_date_manual_override"] = True
    if "timezone" in patch and not patch["timezone"]:
        patch["timezone"] = "UTC"
    for key, value in patch.items():
        setattr(obj, key, value)
    if any(k in patch for k in ("po_header_id", "shipment_header_id", "po_number", "shipment_number")):
        po_number, shipment_number = _resolve_parent_numbers(
            db=db,
            po_header_id=obj.po_header_id,
            shipment_header_id=obj.shipment_header_id,
        )
        if not obj.po_number:
            obj.po_number = po_number
        if not obj.shipment_number:
            obj.shipment_number = shipment_number
    obj.last_changed_by = current_user_email
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise ConcurrencyError("Event instance was updated by another transaction.") from exc
    db.refresh(obj)
    return get_event_instance(db, obj.id)


def delete_event_instance(db: Session, row_id: int) -> bool:
    obj = db.get(EventInstance, row_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
