from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from requests import RequestException
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.event_profile import EventInstance, EventProfile, ProfileEventMap
from app.models.purchase_order import PurchaseOrderHeader
from app.models.shipment import ShipmentHeader
from app.schemas.timeline import (
    TimelineDryRunItem,
    TimelineDryRunRequest,
    TimelinePreviewItem,
    TimelinePreviewRequest,
    TimelinePreviewResponse,
    TimelineSaveItem,
    TimelineSaveRequest,
    TimelineSaveResponse,
)
from app.services.timeline_service import TimelineService
from app.api.deps.request_identity import get_request_email
from app.services.document_lock_service import (
    DocumentLockFailure,
    DocumentLockService,
    LOCK_TOKEN_HEADER,
)

router = APIRouter()


def _get_user_email(request: Request) -> str:
    return get_request_email(request)


def _normalize_object_type(value: str) -> str:
    normalized = (value or "").strip().upper()
    if normalized not in {"PURCHASE_ORDER", "SHIPMENT"}:
        raise ValueError("object_type must be PURCHASE_ORDER or SHIPMENT.")
    return normalized


def _parent_filter(object_type: str, parent_id: int):
    if object_type == "PURCHASE_ORDER":
        return EventInstance.po_header_id == parent_id
    return EventInstance.shipment_header_id == parent_id


def _parent_fk_values(object_type: str, parent_id: int) -> dict[str, int | None]:
    if object_type == "PURCHASE_ORDER":
        return {"po_header_id": parent_id, "shipment_header_id": None}
    return {"po_header_id": None, "shipment_header_id": parent_id}


def _resolve_parent_numbers(db: Session, object_type: str, parent_id: int) -> tuple[str | None, str | None]:
    if object_type == "PURCHASE_ORDER":
        row = (
            db.query(PurchaseOrderHeader.po_number)
            .filter(PurchaseOrderHeader.id == parent_id)
            .first()
        )
        return (str(row[0]) if row and row[0] else None, None)
    row = (
        db.query(ShipmentHeader.shipment_number)
        .filter(ShipmentHeader.id == parent_id)
        .first()
    )
    return (None, str(row[0]) if row and row[0] else None)


def _resolve_parent_created_at(
    db: Session,
    object_type: str,
    parent_id: int,
) -> datetime | None:
    if object_type == "PURCHASE_ORDER":
        row = (
            db.query(PurchaseOrderHeader.created_at)
            .filter(PurchaseOrderHeader.id == parent_id)
            .first()
        )
        return _parse_datetime(row[0]) if row and row[0] is not None else None
    row = (
        db.query(ShipmentHeader.created_at)
        .filter(ShipmentHeader.id == parent_id)
        .first()
    )
    return _parse_datetime(row[0]) if row and row[0] is not None else None


def _resolve_effective_start_date(
    db: Session,
    object_type: str,
    parent_id: int,
    requested_start_date: datetime | None,
) -> datetime | None:
    parent_created_at = _resolve_parent_created_at(
        db=db,
        object_type=object_type,
        parent_id=parent_id,
    )
    if parent_created_at is not None:
        return parent_created_at
    return _parse_datetime(requested_start_date)


def _parse_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if len(text) == 10:
                return datetime.fromisoformat(text)
            normalized = text.replace(" ", "T")
            if len(normalized) == 16:
                normalized = f"{normalized}:00"
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _normalize_status(status: str | None, actual_date: datetime | None) -> str:
    candidate = (status or "").strip().upper()
    if candidate in {"PLANNED", "COMPLETED", "DELAYED"}:
        return candidate
    if actual_date is not None:
        return "COMPLETED"
    return "PLANNED"


def _planned_date_changed(
    saved_planned_date: datetime | None,
    recalculated_planned_date: datetime | None,
) -> bool:
    def _normalize(value: datetime | None) -> datetime | None:
        parsed = _parse_datetime(value)
        if parsed is None:
            return None
        return parsed.replace(second=0, microsecond=0)

    saved_planned_date = _normalize(saved_planned_date)
    recalculated_planned_date = _normalize(recalculated_planned_date)
    if saved_planned_date is None and recalculated_planned_date is None:
        return False
    if saved_planned_date is None or recalculated_planned_date is None:
        return True
    return saved_planned_date != recalculated_planned_date


def _has_execution_started(
    existing_rows: list[EventInstance],
    actual_date_overrides: dict[str, datetime] | None = None,
) -> bool:
    if any(row.actual_date is not None for row in existing_rows):
        return True
    if actual_date_overrides:
        for value in actual_date_overrides.values():
            if value is not None:
                return True
    return False


def _ensure_profile_hint(
    db: Session,
    object_type: str,
    context_data: dict,
) -> dict:
    del db
    payload = dict(context_data or {})
    has_profile_id = "profile_id" in payload and payload.get("profile_id") is not None
    has_profile_rule = bool(str(payload.get("profile_rule_slug") or "").strip())
    if has_profile_id or has_profile_rule:
        payload.setdefault("object_type", object_type.upper())
        return payload

    mapping = {
        "PURCHASE_ORDER": "po_events",
        "SHIPMENT": "shipment_events",
    }
    payload["profile_rule_slug"] = mapping.get(object_type.upper())
    payload.setdefault("object_type", object_type.upper())
    return payload


def _build_persisted_preview_items(
    db: Session,
    existing_rows: list[EventInstance],
    existing_by_code: dict[str, EventInstance],
) -> list[TimelinePreviewItem]:
    if not existing_by_code:
        return []

    profile_id = next(
        (row.profile_id for row in existing_rows if row.profile_id is not None),
        None,
    )
    profile_rows: list[ProfileEventMap] = []
    if profile_id is not None:
        profile_rows = (
            db.query(ProfileEventMap)
            .options(
                joinedload(ProfileEventMap.event),
                joinedload(ProfileEventMap.anchor_event),
            )
            .filter(ProfileEventMap.profile_id == profile_id)
            .order_by(ProfileEventMap.sequence.asc(), ProfileEventMap.id.asc())
            .all()
        )

    profile_by_code = {row.event_code: row for row in profile_rows}

    ordered_codes: list[str] = []
    seen_codes: set[str] = set()
    for row in profile_rows:
        code = str(row.event_code or "").strip()
        if not code or code not in existing_by_code or code in seen_codes:
            continue
        seen_codes.add(code)
        ordered_codes.append(code)

    for row in reversed(existing_rows):
        code = str(row.event_code or "").strip()
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)
        ordered_codes.append(code)

    items: list[TimelinePreviewItem] = []
    for event_code in ordered_codes:
        existing = existing_by_code[event_code]
        mapping = profile_by_code.get(event_code)
        event_name = None
        if mapping is not None and mapping.event is not None:
            event_name = mapping.event.event_name
        elif existing.event is not None:
            event_name = existing.event.event_name

        anchor_event_code = mapping.anchor_event_code if mapping is not None else None
        anchor_event_name = (
            mapping.anchor_event.event_name
            if mapping is not None and mapping.anchor_event is not None
            else None
        )
        offset_minutes = int(mapping.offset_days or 0) if mapping is not None else None
        status = _normalize_status(existing.status, existing.actual_date)

        items.append(
            TimelinePreviewItem(
                event_code=event_code,
                event_name=event_name,
                anchor_event_code=anchor_event_code,
                anchor_event_name=anchor_event_name,
                anchor_used_event_code=anchor_event_code,
                anchor_used_event_name=anchor_event_name,
                offset_minutes=offset_minutes,
                is_active=True,
                planned_date=existing.planned_date,
                saved_planned_date=existing.planned_date,
                planned_date_manual_override=bool(existing.planned_date_manual_override),
                baseline_date=existing.baseline_date,
                actual_date=existing.actual_date,
                status=status,
                status_reason=existing.status_reason,
                timezone=existing.timezone,
                is_unsaved_change=False,
            )
        )

    return items


@router.post(
    "/dry-run",
    response_model=list[TimelineDryRunItem],
    status_code=status.HTTP_200_OK,
    summary="Calculate event timeline dry run",
    description=(
        "Evaluates profile/inclusion rules and computes planned dates recursively in memory. "
        "No database writes are performed."
    ),
)
def calculate_timeline_dry_run(
    payload: TimelineDryRunRequest,
    db: Session = Depends(get_db),
):
    service = TimelineService(db=db)
    try:
        return service.calculate_dry_run(
            context_data=payload.context_data,
            start_date=payload.start_date,
        )
    except RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Decision engine request failed: {exc}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/preview",
    response_model=TimelinePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview timeline events (dry-run + persisted actual dates)",
)
def preview_timeline(
    payload: TimelinePreviewRequest,
    db: Session = Depends(get_db),
):
    object_type = _normalize_object_type(payload.object_type)
    effective_start_date = _resolve_effective_start_date(
        db=db,
        object_type=object_type,
        parent_id=payload.parent_id,
        requested_start_date=payload.start_date,
    )
    if effective_start_date is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to resolve timeline start_date from parent document.",
        )
    parent_filter = _parent_filter(object_type, payload.parent_id)

    existing_rows = (
        db.query(EventInstance)
        .options(joinedload(EventInstance.event))
        .filter(parent_filter)
        .order_by(EventInstance.id.desc())
        .all()
    )
    existing_by_code: dict[str, EventInstance] = {}
    for row in existing_rows:
        if row.event_code not in existing_by_code:
            existing_by_code[row.event_code] = row

    if not payload.recalculate:
        items = _build_persisted_preview_items(
            db=db,
            existing_rows=existing_rows,
            existing_by_code=existing_by_code,
        )
        return TimelinePreviewResponse(
            object_type=object_type,
            parent_id=payload.parent_id,
            items=items,
        )

    execution_started = _has_execution_started(
        existing_rows=existing_rows,
        actual_date_overrides=payload.actual_date_overrides,
    )

    fixed_anchor_dates: dict[str, datetime] = {}
    if payload.preserve_actual_dates:
        for event_code, row in existing_by_code.items():
            if row.actual_date is not None:
                fixed_anchor_dates[event_code] = row.actual_date
            elif row.planned_date_manual_override and row.planned_date is not None:
                # Manual planned dates are sticky anchors and must not be recalculated.
                fixed_anchor_dates[event_code] = row.planned_date
    for event_code, actual_date in (payload.actual_date_overrides or {}).items():
        code = str(event_code or "").strip()
        if code and actual_date is not None:
            fixed_anchor_dates[code] = actual_date

    resolved_context = _ensure_profile_hint(db, object_type, payload.context_data)
    service = TimelineService(db=db)
    try:
        profile_id, dry_run = service.calculate_dry_run_with_profile(
            context_data=resolved_context,
            start_date=effective_start_date,
            fixed_anchor_dates=fixed_anchor_dates,
        )
    except RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Decision engine request failed: {exc}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    profile_timezone: str | None = None
    if profile_id is not None:
        profile = db.get(EventProfile, profile_id)
        if profile is not None and profile.timezone:
            profile_timezone = profile.timezone

    items: list[TimelinePreviewItem] = []
    for row in dry_run:
        event_code = str(row.get("event_code") or "").strip()
        if not event_code:
            continue
        recalculated_planned_date = _parse_datetime(row.get("planned_date"))
        planned_date = recalculated_planned_date
        is_active = bool(row.get("is_active"))
        event_name = row.get("event_name")
        anchor_event_code = row.get("anchor_event_code")
        anchor_event_name = row.get("anchor_event_name")
        anchor_used_event_code = row.get("anchor_used_event_code")
        anchor_used_event_name = row.get("anchor_used_event_name")
        offset_minutes = row.get("offset_minutes")

        existing = existing_by_code.get(event_code)
        saved_planned_date = existing.planned_date if existing else None
        planned_date_manual_override = bool(existing.planned_date_manual_override) if existing else False
        if existing and existing.baseline_date is not None:
            baseline_date = existing.baseline_date
        elif not execution_started and planned_date is not None:
            # Before any execution starts, baseline and planned stay aligned.
            baseline_date = planned_date
        else:
            baseline_date = effective_start_date
        actual_date = existing.actual_date if existing else None
        status = existing.status if existing else None
        status_reason = existing.status_reason if existing else None
        timezone = existing.timezone if existing else profile_timezone
        if existing is not None:
            if planned_date_manual_override:
                # Persisted manual plans are sticky until the user changes them.
                planned_date = saved_planned_date
                is_unsaved_change = False
            elif actual_date is not None:
                # Once actual is reported, persisted planned date is frozen.
                planned_date = saved_planned_date
                is_unsaved_change = False
            else:
                anchor_changed = _planned_date_changed(
                    saved_planned_date=saved_planned_date,
                    recalculated_planned_date=recalculated_planned_date,
                )
                planned_date = recalculated_planned_date if anchor_changed else saved_planned_date
                is_unsaved_change = _planned_date_changed(
                    saved_planned_date=saved_planned_date,
                    recalculated_planned_date=planned_date,
                )
        else:
            is_unsaved_change = bool(recalculated_planned_date is not None)

        items.append(
            TimelinePreviewItem(
                event_code=event_code,
                event_name=event_name,
                anchor_event_code=anchor_event_code,
                anchor_event_name=anchor_event_name,
                anchor_used_event_code=anchor_used_event_code,
                anchor_used_event_name=anchor_used_event_name,
                offset_minutes=offset_minutes,
                is_active=is_active,
                planned_date=planned_date,
                saved_planned_date=saved_planned_date,
                planned_date_manual_override=planned_date_manual_override,
                baseline_date=baseline_date,
                actual_date=actual_date,
                status=status,
                status_reason=status_reason,
                timezone=timezone,
                is_unsaved_change=is_unsaved_change,
            )
        )

    return TimelinePreviewResponse(
        object_type=object_type,
        parent_id=payload.parent_id,
        items=items,
    )


@router.post(
    "/save",
    response_model=TimelineSaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Persist timeline events with atomic bulk delete+insert",
)
def save_timeline(
    payload: TimelineSaveRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    object_type = _normalize_object_type(payload.object_type)
    effective_start_date = _resolve_effective_start_date(
        db=db,
        object_type=object_type,
        parent_id=payload.parent_id,
        requested_start_date=payload.start_date,
    )
    parent_filter = _parent_filter(object_type, payload.parent_id)
    parent_fk_values = _parent_fk_values(object_type, payload.parent_id)
    po_number, shipment_number = _resolve_parent_numbers(db, object_type, payload.parent_id)
    user_email = _get_user_email(request)
    lock_token = request.headers.get(LOCK_TOKEN_HEADER)

    existing_rows = db.query(EventInstance).filter(parent_filter).order_by(EventInstance.id.desc()).all()
    execution_started = _has_execution_started(existing_rows=existing_rows)
    existing_by_code: dict[str, EventInstance] = {}
    existing_actual_by_code: dict[str, date] = {}
    existing_manual_planned_by_code: dict[str, date] = {}
    for row in existing_rows:
        if row.event_code not in existing_by_code:
            existing_by_code[row.event_code] = row
        if row.actual_date is not None and row.event_code not in existing_actual_by_code:
            existing_actual_by_code[row.event_code] = row.actual_date
        if (
            row.planned_date_manual_override
            and row.planned_date is not None
            and row.event_code not in existing_manual_planned_by_code
        ):
            existing_manual_planned_by_code[row.event_code] = row.planned_date

    event_map: dict[str, TimelineSaveItem] = {}
    for item in payload.events:
        event_code = (item.event_code or "").strip()
        if not event_code:
            continue
        event_map[event_code] = item
        if item.actual_date is not None:
            execution_started = True

    resolved_context = _ensure_profile_hint(db, object_type, payload.context_data)
    service = TimelineService(db=db)
    profile_id: int | None = None
    profile_version: int | None = None
    profile_timezone: str | None = None

    dry_map: dict[str, dict] = {}
    if payload.recalculate:
        if effective_start_date is None:
            raise HTTPException(
                status_code=400,
                detail="start_date is required when recalculate=true and parent creation date is unavailable.",
            )

        fixed_anchor_dates = dict(existing_actual_by_code)
        fixed_anchor_dates.update(existing_manual_planned_by_code)
        for item in payload.events:
            event_code = (item.event_code or "").strip()
            if not event_code:
                continue
            if item.actual_date is not None:
                fixed_anchor_dates[event_code] = item.actual_date
                continue

            manual_override = item.planned_date_manual_override
            if manual_override is None:
                existing = existing_by_code.get(event_code)
                manual_override = bool(existing.planned_date_manual_override) if existing else False
            if manual_override:
                if item.planned_date is not None:
                    fixed_anchor_dates[event_code] = item.planned_date
                elif event_code in existing_manual_planned_by_code:
                    fixed_anchor_dates[event_code] = existing_manual_planned_by_code[event_code]

        try:
            profile_id, dry_run = service.calculate_dry_run_with_profile(
                context_data=resolved_context,
                start_date=effective_start_date,
                fixed_anchor_dates=fixed_anchor_dates,
            )
        except RequestException as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Decision engine request failed: {exc}",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        dry_map = {
            str(row.get("event_code") or "").strip(): row
            for row in dry_run
            if str(row.get("event_code") or "").strip()
        }

        if not event_map:
            for event_code, row in dry_map.items():
                existing = existing_by_code.get(event_code)
                manual_override = bool(existing.planned_date_manual_override) if existing else False
                default_planned = _parse_datetime(row.get("planned_date"))
                if manual_override and existing is not None and existing.planned_date is not None:
                    default_planned = existing.planned_date
                event_map[event_code] = TimelineSaveItem(
                    event_code=event_code,
                    is_active=bool(row.get("is_active")),
                    planned_date=default_planned,
                    planned_date_manual_override=manual_override,
                )
        else:
            for event_code, row in dry_map.items():
                existing_item = event_map.get(event_code)
                if existing_item is None:
                    continue
                existing_row = existing_by_code.get(event_code)
                manual_override = existing_item.planned_date_manual_override
                if manual_override is None:
                    manual_override = bool(existing_row.planned_date_manual_override) if existing_row else False
                manual_override = bool(manual_override)
                calculated_planned_date = _parse_datetime(row.get("planned_date"))
                final_planned_date = (
                    existing_item.planned_date
                    if manual_override and existing_item.planned_date is not None
                    else calculated_planned_date
                )
                if manual_override and final_planned_date is None and existing_row is not None:
                    final_planned_date = existing_row.planned_date
                event_map[event_code] = TimelineSaveItem(
                    event_code=event_code,
                    is_active=bool(row.get("is_active")),
                    baseline_date=existing_item.baseline_date,
                    planned_date=final_planned_date,
                    planned_date_manual_override=manual_override,
                    actual_date=existing_item.actual_date,
                    status=existing_item.status,
                )

    rows_to_insert: list[dict] = []
    if profile_id is None:
        try:
            profile_id = service.resolve_profile_id(resolved_context)
        except Exception:
            profile_id = None
    if profile_id is not None:
        profile = db.get(EventProfile, profile_id)
        if profile is not None:
            profile_version = profile.profile_version
            profile_timezone = profile.timezone
    for event_code, item in event_map.items():
        if not item.is_active:
            continue
        existing = existing_by_code.get(event_code)
        actual_date = item.actual_date if item.actual_date is not None else existing_actual_by_code.get(event_code)
        baseline_date = item.baseline_date
        calculated_planned_date = _parse_datetime(dry_map.get(event_code, {}).get("planned_date"))
        manual_override = item.planned_date_manual_override
        if manual_override is None:
            if item.planned_date is not None:
                if calculated_planned_date is not None:
                    manual_override = item.planned_date != calculated_planned_date
                elif existing is not None:
                    manual_override = item.planned_date != existing.planned_date
                else:
                    manual_override = False
            else:
                manual_override = bool(existing.planned_date_manual_override) if existing else False
        manual_override = bool(manual_override)
        planned_date = item.planned_date
        if manual_override:
            if planned_date is None and existing is not None:
                planned_date = existing.planned_date
        else:
            if planned_date is None and calculated_planned_date is not None:
                planned_date = calculated_planned_date
            if planned_date is None and existing is not None:
                planned_date = existing.planned_date
        if planned_date is None and actual_date is not None:
            planned_date = actual_date
        user_changed_manual_plan = (
            bool(item.planned_date_manual_override)
            and item.planned_date is not None
            and (existing is None or item.planned_date != existing.planned_date)
        )
        if actual_date is not None and existing is not None and not user_changed_manual_plan:
            # Keep persisted planned date fixed after actual is reported unless
            # user explicitly enters a new manual planned date.
            planned_date = existing.planned_date
            manual_override = bool(existing.planned_date_manual_override)
        if execution_started:
            # After first actual date, baseline freezes.
            if baseline_date is None and existing is not None:
                baseline_date = existing.baseline_date
            if baseline_date is None:
                baseline_date = planned_date or effective_start_date
        else:
            # Planning phase: baseline tracks latest planned date.
            baseline_date = planned_date or baseline_date or effective_start_date
        status = _normalize_status(item.status or (existing.status if existing else None), actual_date)
        status_reason = item.status_reason or (existing.status_reason if existing else None)
        timezone = item.timezone or (existing.timezone if existing else None) or profile_timezone or "UTC"

        row = {
            "parent_id": payload.parent_id,
            "event_code": event_code,
            "baseline_date": baseline_date,
            "planned_date": planned_date,
            "planned_date_manual_override": manual_override,
            "actual_date": actual_date,
            "status": status,
            "status_reason": status_reason,
            "timezone": timezone,
            "profile_id": profile_id,
            "profile_version": profile_version,
            "po_number": po_number,
            "shipment_number": shipment_number,
            "created_by": user_email,
            "last_changed_by": user_email,
            **parent_fk_values,
        }
        rows_to_insert.append(row)

    lock_service = DocumentLockService(db)
    try:
        lock_service.validate_for_write(
            object_type=object_type,
            document_id=payload.parent_id,
            owner_email=user_email,
            lock_token=lock_token,
        )
        delete_result = db.execute(delete(EventInstance).where(parent_filter))
        if rows_to_insert:
            db.execute(insert(EventInstance), rows_to_insert)
        db.commit()
    except DocumentLockFailure as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=exc.to_detail())
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Timeline save failed: {exc}")

    return TimelineSaveResponse(
        object_type=object_type,
        parent_id=payload.parent_id,
        deleted_count=delete_result.rowcount or 0,
        inserted_count=len(rows_to_insert),
    )
