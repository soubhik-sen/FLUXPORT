from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

import requests
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.event_profile import EventProfile, ProfileEventMap
from app.services.decision_engine_client import evaluate as evaluate_decision


class TimelineService:
    """
    Dry-run planner for dependency-based events.

    Pure-function guarantee: this service only reads DB + external rule engine;
    it never writes to the database.
    """

    def __init__(
        self,
        db: Session,
        decision_engine_url: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        self.db = db
        self.decision_engine_url = (decision_engine_url or settings.DECISION_ENGINE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def calculate_dry_run(
        self,
        context_data: dict[str, Any],
        start_date: datetime | date,
        fixed_anchor_dates: dict[str, datetime | date] | None = None,
    ) -> list[dict[str, Any]]:
        _, output = self.calculate_dry_run_with_profile(
            context_data=context_data,
            start_date=start_date,
            fixed_anchor_dates=fixed_anchor_dates,
        )
        return output

    def calculate_dry_run_with_profile(
        self,
        context_data: dict[str, Any],
        start_date: datetime | date,
        fixed_anchor_dates: dict[str, datetime | date] | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        start_dt = self._normalize_datetime(start_date)
        fixed_anchor_dates = fixed_anchor_dates or {}
        normalized_fixed_dates = {
            str(code).strip(): self._normalize_datetime(value)
            for code, value in fixed_anchor_dates.items()
            if str(code).strip() and value is not None
        }

        profile_id = self._resolve_profile_id(context_data)
        rows = self._get_profile_events(profile_id)
        if not rows:
            return profile_id, []

        @lru_cache(maxsize=512)
        def evaluate_inclusion_rule_cached(rule_slug: str) -> bool:
            response_payload = self._evaluate_rule(rule_slug, context_data)
            return self._extract_boolean_result(response_payload, rule_slug)

        nodes: dict[str, dict[str, Any]] = {}
        ordered_event_codes: list[str] = []
        for row in rows:
            is_active = True
            if row.inclusion_rule_id:
                is_active = evaluate_inclusion_rule_cached(row.inclusion_rule_id)

            nodes[row.event_code] = {
                "event_code": row.event_code,
                "event_name": row.event.event_name if row.event else None,
                "anchor_event_code": row.anchor_event_code,
                "anchor_event_name": row.anchor_event.event_name if row.anchor_event else None,
                "offset_minutes": int(row.offset_days or 0),
                "is_active": is_active,
            }
            ordered_event_codes.append(row.event_code)

        planned_cache: dict[str, datetime] = {}
        anchor_used_cache: dict[str, str | None] = {}

        def resolve_planned_date(event_code: str, trail: frozenset[str]) -> datetime:
            if event_code in planned_cache:
                return planned_cache[event_code]

            node = nodes.get(event_code)
            if node is None:
                return start_dt

            if event_code in normalized_fixed_dates:
                fixed = normalized_fixed_dates[event_code]
                _, anchor_used = resolve_active_anchor_date(
                    node["anchor_event_code"],
                    trail=trail | {event_code},
                )
                anchor_used_cache[event_code] = anchor_used
                planned_cache[event_code] = fixed
                return fixed

            anchor_date, anchor_used = resolve_active_anchor_date(
                node["anchor_event_code"],
                trail=trail | {event_code},
            )
            planned = anchor_date + timedelta(minutes=node["offset_minutes"])
            planned_cache[event_code] = planned
            anchor_used_cache[event_code] = anchor_used
            return planned

        def resolve_active_anchor_date(
            anchor_event_code: str | None,
            trail: frozenset[str],
        ) -> tuple[datetime, str | None]:
            current = anchor_event_code
            local_trail = set(trail)

            while current:
                if current in local_trail:
                    raise ValueError(f"Cyclic dependency detected while resolving '{current}'.")
                local_trail.add(current)

                anchor_node = nodes.get(current)
                if anchor_node is None:
                    # Anchor not in profile map: fall back to start boundary.
                    return start_dt, None

                if anchor_node["is_active"]:
                    return (
                        resolve_planned_date(current, trail=frozenset(local_trail)),
                        current,
                    )

                # Anchor is skipped: climb to the anchor's anchor.
                current = anchor_node["anchor_event_code"]

            return start_dt, None

        output: list[dict[str, Any]] = []
        for event_code in ordered_event_codes:
            node = nodes[event_code]
            planned_date: datetime | None = None
            if node["is_active"]:
                planned_date = resolve_planned_date(event_code, trail=frozenset())

            anchor_used_code = anchor_used_cache.get(event_code)
            anchor_used_name = (
                nodes.get(anchor_used_code, {}).get("event_name")
                if anchor_used_code
                else None
            )

            output.append(
                {
                    "event_code": event_code,
                    "event_name": node.get("event_name"),
                    "anchor_event_code": node.get("anchor_event_code"),
                    "anchor_event_name": node.get("anchor_event_name"),
                    "anchor_used_event_code": anchor_used_code,
                    "anchor_used_event_name": anchor_used_name,
                    "offset_minutes": node.get("offset_minutes"),
                    "planned_date": planned_date.isoformat() if planned_date else None,
                    "is_active": bool(node["is_active"]),
                }
            )

        return profile_id, output

    def resolve_profile_id(self, context_data: dict[str, Any]) -> int:
        return self._resolve_profile_id(context_data)

    def _resolve_profile_id(self, context_data: dict[str, Any]) -> int:
        context_data = self._enrich_context_for_profile_resolution(context_data)
        direct_profile = context_data.get("profile_id")
        if isinstance(direct_profile, int):
            return direct_profile
        if isinstance(direct_profile, str) and direct_profile.strip().isdigit():
            return int(direct_profile.strip())

        object_type = str(context_data.get("object_type") or "").strip().upper()
        if not settings.EVENTS_PROFILE_ENABLED:
            return self._resolve_default_profile_id(object_type)

        profile_rule_slug = str(context_data.get("profile_rule_slug") or "").strip()
        if not profile_rule_slug:
            raise ValueError(
                "context_data.profile_id or context_data.profile_rule_slug is required for profile resolution."
            )
        candidate_rule_slugs = self._candidate_profile_rule_slugs(profile_rule_slug, object_type)

        last_error: Exception | None = None
        for candidate_slug in candidate_rule_slugs:
            try:
                response_payload = self._evaluate_rule(candidate_slug, context_data)
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code == 404:
                    last_error = exc
                    continue
                raise

            profile_id = self._extract_profile_id(response_payload)
            if profile_id is None:
                profile_id = self._extract_profile_id_from_name(response_payload)
            if profile_id is not None:
                return profile_id

            last_error = ValueError(
                f"Rule '{candidate_slug}' did not return profile_id/profile_name in result payload."
            )

        if last_error:
            raise ValueError(
                f"Unable to resolve profile for object_type '{object_type}' using rule slug '{profile_rule_slug}'."
            ) from last_error
        raise ValueError("Unable to resolve profile_id from decision response.")

    def _resolve_default_profile_id(self, object_type: str) -> int:
        default_profile_name = {
            "PURCHASE_ORDER": "PO_EVENTS_DEFAULT_V1",
            "SHIPMENT": "SHIPMENT_EVENTS_DEFAULT_V1",
        }.get(object_type)
        if not default_profile_name:
            raise ValueError(
                "context_data.object_type must be PURCHASE_ORDER or SHIPMENT for default event profile resolution."
            )

        row = (
            self.db.query(EventProfile.id)
            .filter(EventProfile.name == default_profile_name)
            .first()
        )
        if row:
            return int(row[0])

        row = (
            self.db.query(EventProfile.id)
            .filter(EventProfile.name.ilike(default_profile_name))
            .first()
        )
        if row:
            return int(row[0])

        raise ValueError(
            f"Default event profile '{default_profile_name}' was not found for object_type '{object_type}'."
        )

    def _enrich_context_for_profile_resolution(self, context_data: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(context_data or {})
        object_type = str(enriched.get("object_type") or "").strip().upper()

        if object_type == "PURCHASE_ORDER":
            po_number = str(enriched.get("purchase_order_number") or "").strip()
            if not po_number:
                po_number = str(enriched.get("po_number") or "").strip()
            if po_number:
                enriched.setdefault("po_number", po_number)
                enriched["purchase_order_number"] = po_number
            return enriched

        if object_type == "SHIPMENT":
            shipment_number = str(enriched.get("shipment_number") or "").strip()
            if shipment_number:
                enriched["shipment_number"] = shipment_number
            return enriched

        return enriched

    @staticmethod
    def _candidate_profile_rule_slugs(profile_rule_slug: str, object_type: str) -> list[str]:
        fallback_slugs = {
            "PURCHASE_ORDER": ["po_events", "purchase_order_default_profile_v1"],
            "SHIPMENT": ["shipment_events", "shipment_default_profile_v1"],
        }.get(object_type, [])

        ordered = [profile_rule_slug, *fallback_slugs]
        deduped: list[str] = []
        seen: set[str] = set()
        for slug in ordered:
            normalized = str(slug or "").strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
        return deduped

    def _get_profile_events(self, profile_id: int) -> list[ProfileEventMap]:
        return (
            self.db.query(ProfileEventMap)
            .options(
                joinedload(ProfileEventMap.event),
                joinedload(ProfileEventMap.anchor_event),
            )
            .filter(ProfileEventMap.profile_id == profile_id)
            .order_by(ProfileEventMap.sequence.asc(), ProfileEventMap.id.asc())
            .all()
        )

    @staticmethod
    def _normalize_datetime(value: datetime | date) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        raise ValueError("Expected date or datetime for start_date.")

    def _evaluate_rule(self, table_slug: str, context_data: dict[str, Any]) -> dict[str, Any]:
        context_payload = dict(context_data or {})
        payload: dict[str, Any] = {
            "table_slug": table_slug,
            "context": context_payload,
        }
        return evaluate_decision(
            payload,
            timeout_seconds=self.timeout_seconds,
            decision_engine_url=self.decision_engine_url,
        )

    @staticmethod
    def _extract_profile_id(response_payload: dict[str, Any]) -> int | None:
        result = response_payload.get("result")

        if isinstance(result, int):
            return result
        if isinstance(result, str) and result.strip().isdigit():
            return int(result.strip())
        if isinstance(result, dict):
            for key in ("profile_id", "event_profile_id", "id"):
                value = result.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.strip().isdigit():
                    return int(value.strip())

            if len(result) == 1:
                only_value = next(iter(result.values()))
                if isinstance(only_value, int):
                    return only_value
                if isinstance(only_value, str) and only_value.strip().isdigit():
                    return int(only_value.strip())

        return None

    def _extract_profile_id_from_name(self, response_payload: dict[str, Any]) -> int | None:
        profile_name = self._extract_profile_name(response_payload)
        if not profile_name:
            return None

        row = (
            self.db.query(EventProfile.id)
            .filter(EventProfile.name == profile_name)
            .first()
        )
        if row:
            return int(row[0])

        row = (
            self.db.query(EventProfile.id)
            .filter(EventProfile.name.ilike(profile_name))
            .first()
        )
        if row:
            return int(row[0])
        return None

    @staticmethod
    def _extract_profile_name(response_payload: dict[str, Any]) -> str | None:
        result = response_payload.get("result")
        if isinstance(result, dict):
            for key in ("profile_name", "event_profile_name", "name", "profile"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            if len(result) == 1:
                only_value = next(iter(result.values()))
                if isinstance(only_value, str) and only_value.strip():
                    return only_value.strip()
        if isinstance(result, str) and result.strip() and not result.strip().isdigit():
            return result.strip()
        return None

    @staticmethod
    def _extract_boolean_result(response_payload: dict[str, Any], rule_slug: str) -> bool:
        result = response_payload.get("result")

        if isinstance(result, bool):
            return result

        if isinstance(result, dict):
            # Strict boolean requirement with predictable keys.
            for key in ("is_included", "include", "is_active", "value", "result"):
                value = result.get(key)
                if isinstance(value, bool):
                    return value

            if len(result) == 1:
                only_value = next(iter(result.values()))
                if isinstance(only_value, bool):
                    return only_value

        # Include a compact payload excerpt for fast debugging.
        snippet = json.dumps(result, default=str)[:200]
        raise ValueError(
            f"Inclusion rule '{rule_slug}' must return a strict boolean result. Got: {snippet}"
        )
