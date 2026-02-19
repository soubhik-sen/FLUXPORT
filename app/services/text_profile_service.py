from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.decision.attribute_registry import get_attribute_registry
from app.models.logistics_lookups import PortLookup, ShipTypeLookup, TransportModeLookup
from app.models.partner_master import PartnerMaster
from app.models.po_lookups import PurchaseOrderTypeLookup, PurchaseOrgLookup
from app.models.text_lookups import TextTypeLookup
from app.models.text_profile import (
    POText,
    ProfileTextMap,
    ProfileTextValue,
    ShipmentText,
    TextProfile,
    TextProfileRule,
)
from app.models.user_attributes import UserAttribute
from app.models.user_countries import UserCountry
from app.models.users import User
from app.services.decision_engine_client import evaluate as evaluate_decision

logger = logging.getLogger(__name__)


@dataclass
class ResolvedTextRow:
    text_type_id: int
    text_type_code: str | None
    text_type_name: str | None
    language: str
    text_value: str
    is_editable: bool
    is_mandatory: bool
    source: str


@dataclass
class ResolvedTextProfile:
    profile_id: int | None
    profile_name: str | None
    profile_version: int | None
    language: str
    country_code: str | None
    source: str
    texts: list[ResolvedTextRow]


def _today() -> date:
    return date.today()


def _normalize_language(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return "en"
    return raw.replace("_", "-")


def _normalize_country(value: str | None) -> str | None:
    raw = (value or "").strip().upper()
    return raw or None


def _is_effective_on(
    effective_from: date | None,
    effective_to: date | None,
    on_date: date,
) -> bool:
    if effective_from is not None and effective_from > on_date:
        return False
    if effective_to is not None and effective_to < on_date:
        return False
    return True


class TextProfileService:
    @staticmethod
    def resolve_po_text_profile(
        db: Session,
        *,
        user_email: str | None,
        context: dict[str, Any],
        language_override: str | None = None,
        country_override: str | None = None,
    ) -> ResolvedTextProfile:
        return TextProfileService._resolve_text_profile(
            db,
            object_type="PO",
            table_slug="po_text_profile",
            user_email=user_email,
            context=context,
            language_override=language_override,
            country_override=country_override,
        )

    @staticmethod
    def resolve_shipment_text_profile(
        db: Session,
        *,
        user_email: str | None,
        context: dict[str, Any],
        language_override: str | None = None,
        country_override: str | None = None,
    ) -> ResolvedTextProfile:
        return TextProfileService._resolve_text_profile(
            db,
            object_type="SHIPMENT",
            table_slug="shipment_text_profile",
            user_email=user_email,
            context=context,
            language_override=language_override,
            country_override=country_override,
        )

    @staticmethod
    def resolve_locale_context(
        db: Session,
        *,
        user_email: str | None,
        language_override: str | None = None,
        country_override: str | None = None,
    ) -> tuple[str, str | None]:
        if language_override or country_override:
            return (
                _normalize_language(language_override),
                _normalize_country(country_override),
            )
        if not user_email:
            return ("en", None)

        user = db.query(User).filter(User.email == user_email).first()
        if user is None:
            return ("en", None)

        attrs = (
            db.query(UserAttribute)
            .filter(UserAttribute.user_id == user.id)
            .filter(UserAttribute.key.in_(["preferred_language", "language"]))
            .all()
        )
        language: str | None = None
        for key in ("preferred_language", "language"):
            row = next(
                (
                    attr
                    for attr in attrs
                    if (attr.key or "").strip().lower() == key
                    and (attr.value or "").strip()
                ),
                None,
            )
            if row is not None:
                language = row.value
                break

        country_row = (
            db.query(UserCountry.country_code)
            .filter(UserCountry.user_id == user.id)
            .order_by(UserCountry.id.asc())
            .first()
        )
        country = country_row[0] if country_row else None
        return (_normalize_language(language), _normalize_country(country))

    @staticmethod
    def resolve_text_type_id(
        db: Session,
        *,
        text_type_id: int | None = None,
        text_type_code: str | None = None,
        text_type_name: str | None = None,
    ) -> int | None:
        if text_type_id is not None:
            exists = (
                db.query(TextTypeLookup.id)
                .filter(TextTypeLookup.id == int(text_type_id))
                .first()
            )
            return int(text_type_id) if exists else None

        code = (text_type_code or "").strip()
        if code:
            row = (
                db.query(TextTypeLookup.id)
                .filter(TextTypeLookup.text_type_code == code)
                .first()
            )
            if row is not None:
                return int(row[0])

        name = (text_type_name or "").strip()
        if name:
            row = (
                db.query(TextTypeLookup.id)
                .filter(TextTypeLookup.text_type_name == name)
                .first()
            )
            if row is not None:
                return int(row[0])

        return None

    @staticmethod
    def list_po_runtime_texts(db: Session, po_id: int) -> list[POText]:
        return (
            db.query(POText)
            .filter(POText.po_header_id == po_id)
            .order_by(POText.id.asc())
            .all()
        )

    @staticmethod
    def list_shipment_runtime_texts(db: Session, shipment_id: int) -> list[ShipmentText]:
        return (
            db.query(ShipmentText)
            .filter(ShipmentText.shipment_header_id == shipment_id)
            .order_by(ShipmentText.id.asc())
            .all()
        )

    @staticmethod
    def upsert_po_runtime_texts(
        db: Session,
        *,
        po_id: int,
        rows: list[dict[str, Any]],
        user_email: str | None,
        profile_id: int | None,
        profile_version: int | None,
        mark_user_edited: bool,
    ) -> list[POText]:
        existing = {
            (int(row.text_type_id), _normalize_language(row.language)): row
            for row in TextProfileService.list_po_runtime_texts(db, po_id)
        }
        actor = user_email or "system@local"

        for payload in rows:
            text_type_id = TextProfileService.resolve_text_type_id(
                db,
                text_type_id=payload.get("text_type_id"),
                text_type_code=payload.get("text_type_code"),
                text_type_name=payload.get("text_type_name"),
            )
            if text_type_id is None:
                continue
            language = _normalize_language(payload.get("language"))
            text_value = (payload.get("text_value") or "").strip()
            if not text_value:
                continue

            key = (text_type_id, language)
            current = existing.get(key)
            if current is None:
                current = POText(
                    po_header_id=po_id,
                    profile_id=profile_id,
                    profile_version=profile_version,
                    text_type_id=text_type_id,
                    language=language,
                    text_value=text_value,
                    is_user_edited=mark_user_edited,
                    created_by=actor,
                    last_changed_by=actor,
                )
                db.add(current)
                existing[key] = current
            else:
                current.profile_id = profile_id
                current.profile_version = profile_version
                current.text_value = text_value
                current.is_user_edited = bool(current.is_user_edited or mark_user_edited)
                current.last_changed_by = actor

        db.flush()
        return TextProfileService.list_po_runtime_texts(db, po_id)

    @staticmethod
    def upsert_shipment_runtime_texts(
        db: Session,
        *,
        shipment_id: int,
        rows: list[dict[str, Any]],
        user_email: str | None,
        profile_id: int | None,
        profile_version: int | None,
        mark_user_edited: bool,
    ) -> list[ShipmentText]:
        existing = {
            (int(row.text_type_id), _normalize_language(row.language)): row
            for row in TextProfileService.list_shipment_runtime_texts(db, shipment_id)
        }
        actor = user_email or "system@local"

        for payload in rows:
            text_type_id = TextProfileService.resolve_text_type_id(
                db,
                text_type_id=payload.get("text_type_id"),
                text_type_code=payload.get("text_type_code"),
                text_type_name=payload.get("text_type_name"),
            )
            if text_type_id is None:
                continue
            language = _normalize_language(payload.get("language"))
            text_value = (payload.get("text_value") or "").strip()
            if not text_value:
                continue

            key = (text_type_id, language)
            current = existing.get(key)
            if current is None:
                current = ShipmentText(
                    shipment_header_id=shipment_id,
                    profile_id=profile_id,
                    profile_version=profile_version,
                    text_type_id=text_type_id,
                    language=language,
                    text_value=text_value,
                    is_user_edited=mark_user_edited,
                    created_by=actor,
                    last_changed_by=actor,
                )
                db.add(current)
                existing[key] = current
            else:
                current.profile_id = profile_id
                current.profile_version = profile_version
                current.text_value = text_value
                current.is_user_edited = bool(current.is_user_edited or mark_user_edited)
                current.last_changed_by = actor

        db.flush()
        return TextProfileService.list_shipment_runtime_texts(db, shipment_id)

    @staticmethod
    def _resolve_text_profile(
        db: Session,
        *,
        object_type: str,
        table_slug: str,
        user_email: str | None,
        context: dict[str, Any],
        language_override: str | None,
        country_override: str | None,
    ) -> ResolvedTextProfile:
        language, country_code = TextProfileService.resolve_locale_context(
            db,
            user_email=user_email,
            language_override=language_override,
            country_override=country_override,
        )

        preferred_profile_id: int | None = None
        preferred_profile_name: str | None = None
        preferred_profile_version: int | None = None

        if settings.TEXT_PROFILE_RESOLVE_MODE == "decision_then_db":
            decision_context = TextProfileService._build_decision_context(
                db,
                object_type=object_type,
                context=context,
                language=language,
                country_code=country_code,
            )
            decision = TextProfileService._resolve_from_decision_engine(
                db,
                table_slug=table_slug,
                context=decision_context,
            )
            if decision is not None:
                preferred_profile_id = decision.profile_id
                preferred_profile_name = decision.profile_name
                preferred_profile_version = decision.profile_version
                if decision.texts:
                    TextProfileService._audit(
                        object_type=object_type,
                        source="decision_engine",
                        profile_id=decision.profile_id,
                        text_count=len(decision.texts),
                        language=language,
                        country_code=country_code,
                    )
                    return decision

        resolved = TextProfileService._resolve_from_db_rules(
            db,
            object_type=object_type,
            language=language,
            country_code=country_code,
            preferred_profile_id=preferred_profile_id,
            preferred_profile_name=preferred_profile_name,
            preferred_profile_version=preferred_profile_version,
            preferred_from_decision=(
                settings.TEXT_PROFILE_RESOLVE_MODE == "decision_then_db"
                and (preferred_profile_id is not None or bool(preferred_profile_name))
            ),
        )
        TextProfileService._audit(
            object_type=object_type,
            source=resolved.source,
            profile_id=resolved.profile_id,
            text_count=len(resolved.texts),
            language=language,
            country_code=country_code,
        )
        return resolved

    @staticmethod
    def _resolve_from_decision_engine(
        db: Session,
        *,
        table_slug: str,
        context: dict[str, Any],
    ) -> ResolvedTextProfile | None:
        try:
            payload = evaluate_decision(
                {"table_slug": table_slug, "context": context},
                timeout_seconds=8,
            )
        except Exception as exc:
            logger.info("text_profile_decision_engine_fallback slug=%s error=%s", table_slug, exc)
            return None

        result = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            return None

        profile_id = TextProfileService._as_int(
            result.get("profile_id") or result.get("text_profile_id")
        )
        profile_name = TextProfileService._as_text(
            result.get("profile_name") or result.get("text_profile_name") or result.get("profile")
        )
        profile_version = TextProfileService._as_int(result.get("profile_version"))
        language = _normalize_language(result.get("language") or context.get("language"))
        country_code = _normalize_country(result.get("country_code") or context.get("country_code"))

        rows = result.get("texts")
        text_rows: list[ResolvedTextRow] = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                text_type_id = TextProfileService.resolve_text_type_id(
                    db,
                    text_type_id=TextProfileService._as_int(row.get("text_type_id")),
                    text_type_code=TextProfileService._as_text(row.get("text_type_code")),
                    text_type_name=TextProfileService._as_text(row.get("text_type_name")),
                )
                if text_type_id is None:
                    continue
                lookup = db.query(TextTypeLookup).filter(TextTypeLookup.id == text_type_id).first()
                text_rows.append(
                    ResolvedTextRow(
                        text_type_id=text_type_id,
                        text_type_code=lookup.text_type_code if lookup else None,
                        text_type_name=lookup.text_type_name if lookup else None,
                        language=_normalize_language(row.get("language") or language),
                        text_value=TextProfileService._as_text(row.get("text_value")) or "",
                        is_editable=bool(row.get("is_editable", True)),
                        is_mandatory=bool(row.get("is_mandatory", False)),
                        source="decision_engine",
                    )
                )

        if not text_rows and profile_id is None and not profile_name:
            return None
        return ResolvedTextProfile(
            profile_id=profile_id,
            profile_name=profile_name,
            profile_version=profile_version,
            language=language,
            country_code=country_code,
            source="decision_engine",
            texts=text_rows,
        )

    @staticmethod
    def _build_decision_context(
        db: Session,
        *,
        object_type: str,
        context: dict[str, Any],
        language: str,
        country_code: str | None,
    ) -> dict[str, Any]:
        # Include locale keys for decision tables and backfill commonly expected keys
        # from request ids to avoid "missing attribute" evaluation failures.
        payload: dict[str, Any] = {
            **context,
            "language": language,
            "country_code": country_code,
        }
        object_key = (object_type or "").strip().upper()
        if object_key == "PO":
            TextProfileService._enrich_po_decision_context(db, payload)
        elif object_key == "SHIPMENT":
            TextProfileService._enrich_shipment_decision_context(db, payload)

        for attr_key in TextProfileService._decision_attribute_keys_for_object_type(object_key):
            payload.setdefault(attr_key, None)
        return payload

    @staticmethod
    def _decision_attribute_keys_for_object_type(object_type: str) -> set[str]:
        engine_object_type = "PURCHASE_ORDER" if object_type == "PO" else object_type
        url = f"{settings.DECISION_ENGINE_URL.rstrip('/')}/proxy/metadata/attributes/{engine_object_type}"
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict):
                attrs = body.get("attributes")
                if isinstance(attrs, list):
                    keys = {
                        str(item.get("key")).strip()
                        for item in attrs
                        if isinstance(item, dict) and item.get("key")
                    }
                    if keys:
                        return keys
        except Exception as exc:
            logger.info(
                "text_profile_attribute_registry_fallback object_type=%s error=%s",
                engine_object_type,
                exc,
            )
        return set(get_attribute_registry(engine_object_type).keys())

    @staticmethod
    def _enrich_po_decision_context(db: Session, payload: dict[str, Any]) -> None:
        type_id = TextProfileService._as_int(payload.get("type_id"))
        if payload.get("po_type") is None and type_id is not None:
            row = (
                db.query(PurchaseOrderTypeLookup.type_code, PurchaseOrderTypeLookup.type_name)
                .filter(PurchaseOrderTypeLookup.id == type_id)
                .first()
            )
            if row is not None:
                payload["po_type"] = row[0] or row[1]

        purchase_org_id = TextProfileService._as_int(payload.get("purchase_org_id"))
        if payload.get("purchase_org") is None and purchase_org_id is not None:
            row = (
                db.query(PurchaseOrgLookup.org_code, PurchaseOrgLookup.org_name)
                .filter(PurchaseOrgLookup.id == purchase_org_id)
                .first()
            )
            if row is not None:
                payload["purchase_org"] = row[0] or row[1]

        vendor_id = TextProfileService._as_int(payload.get("vendor_id"))
        vendor = TextProfileService._partner_lookup(db, vendor_id)
        if payload.get("vendor_code") is None:
            payload["vendor_code"] = vendor[0]
        if payload.get("vendor_name") is None:
            payload["vendor_name"] = vendor[1]

        forwarder_id = TextProfileService._as_int(payload.get("forwarder_id"))
        forwarder = TextProfileService._partner_lookup(db, forwarder_id)
        if payload.get("forwarder_code") is None:
            payload["forwarder_code"] = forwarder[0]
        if payload.get("forwarder_name") is None:
            payload["forwarder_name"] = forwarder[1]

        for key in (
            "po_type",
            "purchase_org",
            "vendor_code",
            "vendor_name",
            "forwarder_code",
            "forwarder_name",
        ):
            payload.setdefault(key, None)

    @staticmethod
    def _enrich_shipment_decision_context(db: Session, payload: dict[str, Any]) -> None:
        type_id = TextProfileService._as_int(payload.get("type_id"))
        if payload.get("shipment_type") is None and type_id is not None:
            row = (
                db.query(ShipTypeLookup.type_code, ShipTypeLookup.type_name)
                .filter(ShipTypeLookup.id == type_id)
                .first()
            )
            if row is not None:
                payload["shipment_type"] = row[0] or row[1]

        mode_id = TextProfileService._as_int(payload.get("mode_id"))
        if payload.get("transport_mode") is None and mode_id is not None:
            row = (
                db.query(TransportModeLookup.mode_code, TransportModeLookup.mode_name)
                .filter(TransportModeLookup.id == mode_id)
                .first()
            )
            if row is not None:
                payload["transport_mode"] = row[0] or row[1]

        carrier_id = TextProfileService._as_int(payload.get("carrier_id"))
        carrier = TextProfileService._partner_lookup(db, carrier_id)
        if payload.get("carrier_code") is None:
            payload["carrier_code"] = carrier[0]
        if payload.get("carrier_name") is None:
            payload["carrier_name"] = carrier[1]

        pol_port_id = TextProfileService._as_int(payload.get("pol_port_id"))
        if payload.get("pol_port_code") is None and pol_port_id is not None:
            row = (
                db.query(PortLookup.port_code)
                .filter(PortLookup.id == pol_port_id)
                .first()
            )
            payload["pol_port_code"] = row[0] if row else None

        pod_port_id = TextProfileService._as_int(payload.get("pod_port_id"))
        if payload.get("pod_port_code") is None and pod_port_id is not None:
            row = (
                db.query(PortLookup.port_code)
                .filter(PortLookup.id == pod_port_id)
                .first()
            )
            payload["pod_port_code"] = row[0] if row else None

        for key in (
            "shipment_type",
            "carrier_name",
            "carrier_code",
            "pol_port_code",
            "pod_port_code",
        ):
            payload.setdefault(key, None)

    @staticmethod
    def _partner_lookup(db: Session, partner_id: int | None) -> tuple[str | None, str | None]:
        if partner_id is None:
            return (None, None)
        row = (
            db.query(
                PartnerMaster.partner_identifier,
                PartnerMaster.trade_name,
                PartnerMaster.legal_name,
            )
            .filter(PartnerMaster.id == partner_id)
            .first()
        )
        if row is None:
            return (None, None)
        partner_code = row[0]
        partner_name = row[1] or row[2]
        return (partner_code, partner_name)

    @staticmethod
    def _resolve_from_db_rules(
        db: Session,
        *,
        object_type: str,
        language: str,
        country_code: str | None,
        preferred_profile_id: int | None,
        preferred_profile_name: str | None,
        preferred_profile_version: int | None,
        preferred_from_decision: bool = False,
    ) -> ResolvedTextProfile:
        profile, matched_preferred = TextProfileService._pick_profile(
            db,
            object_type=object_type,
            language=language,
            country_code=country_code,
            preferred_profile_id=preferred_profile_id,
            preferred_profile_name=preferred_profile_name,
        )
        if profile is None:
            return ResolvedTextProfile(
                profile_id=None,
                profile_name=None,
                profile_version=None,
                language=language,
                country_code=country_code,
                source="db_fallback_empty",
                texts=[],
            )

        maps = (
            db.query(ProfileTextMap, TextTypeLookup)
            .join(TextTypeLookup, TextTypeLookup.id == ProfileTextMap.text_type_id)
            .filter(ProfileTextMap.profile_id == profile.id)
            .filter(ProfileTextMap.is_active == True)
            .order_by(ProfileTextMap.sequence.asc(), ProfileTextMap.id.asc())
            .all()
        )
        map_ids = [row.id for row, _ in maps]
        values_by_map_id: dict[int, list[ProfileTextValue]] = {}
        if map_ids:
            today = _today()
            values = (
                db.query(ProfileTextValue)
                .filter(ProfileTextValue.profile_text_map_id.in_(map_ids))
                .filter(ProfileTextValue.is_active == True)
                .all()
            )
            for value in values:
                if not _is_effective_on(value.valid_from, value.valid_to, today):
                    continue
                values_by_map_id.setdefault(int(value.profile_text_map_id), []).append(value)

        resolved_rows: list[ResolvedTextRow] = []
        for map_row, text_type in maps:
            selected = TextProfileService._pick_profile_text_value(
                values_by_map_id.get(int(map_row.id), []),
                language=language,
                country_code=country_code,
            )
            resolved_rows.append(
                ResolvedTextRow(
                    text_type_id=int(text_type.id),
                    text_type_code=text_type.text_type_code,
                    text_type_name=text_type.text_type_name,
                    language=language,
                    text_value=selected.text_value if selected is not None else "",
                    is_editable=bool(map_row.is_editable),
                    is_mandatory=bool(map_row.is_mandatory),
                    source="db_fallback",
                )
            )

        return ResolvedTextProfile(
            profile_id=int(profile.id),
            profile_name=profile.name,
            profile_version=preferred_profile_version or profile.profile_version,
            language=language,
            country_code=country_code,
            source=(
                "decision_engine"
                if preferred_from_decision and matched_preferred
                else "db_fallback"
            ),
            texts=resolved_rows,
        )

    @staticmethod
    def _pick_profile(
        db: Session,
        *,
        object_type: str,
        language: str,
        country_code: str | None,
        preferred_profile_id: int | None,
        preferred_profile_name: str | None,
    ) -> tuple[TextProfile | None, bool]:
        today = _today()
        base_query = (
            db.query(TextProfile)
            .filter(TextProfile.object_type == object_type)
            .filter(TextProfile.is_active == True)
        )
        if preferred_profile_id is not None:
            profile = base_query.filter(TextProfile.id == preferred_profile_id).first()
            if profile is not None and _is_effective_on(profile.effective_from, profile.effective_to, today):
                return (profile, True)
        if preferred_profile_name:
            name = preferred_profile_name.strip()
            profile = base_query.filter(TextProfile.name == name).first()
            if profile is None and name:
                profile = base_query.filter(TextProfile.name.ilike(f"%{name}%")).first()
            if profile is not None and _is_effective_on(profile.effective_from, profile.effective_to, today):
                return (profile, True)

        rules = (
            db.query(TextProfileRule, TextProfile)
            .join(TextProfile, TextProfile.id == TextProfileRule.profile_id)
            .filter(TextProfileRule.object_type == object_type)
            .filter(TextProfileRule.is_active == True)
            .filter(TextProfile.is_active == True)
            .all()
        )
        candidates: list[tuple[tuple[int, int, int, int], TextProfile]] = []
        for rule, profile in rules:
            if not _is_effective_on(rule.effective_from, rule.effective_to, today):
                continue
            if not _is_effective_on(profile.effective_from, profile.effective_to, today):
                continue

            rule_country = _normalize_country(rule.country_code)
            if rule_country not in {None, "*"} and rule_country != country_code:
                continue
            country_score = 0 if rule_country == country_code and country_code is not None else 1

            rule_language = _normalize_language(rule.language)
            if rule_language not in {"*", language, "en"}:
                continue
            if rule_language == language:
                language_score = 0
            elif rule_language == "en":
                language_score = 1
            else:
                language_score = 2

            priority = int(rule.priority or 1000)
            candidates.append(((priority, country_score, language_score, int(rule.id)), profile))

        if not candidates:
            profile = base_query.order_by(TextProfile.id.asc()).first()
            if profile is not None and _is_effective_on(profile.effective_from, profile.effective_to, today):
                return (profile, False)
            return (None, False)

        candidates.sort(key=lambda row: row[0])
        return (candidates[0][1], False)

    @staticmethod
    def _pick_profile_text_value(
        values: list[ProfileTextValue],
        *,
        language: str,
        country_code: str | None,
    ) -> ProfileTextValue | None:
        if not values:
            return None

        def _country_bucket(raw_country: str | None) -> int:
            norm = _normalize_country(raw_country)
            if country_code and norm == country_code:
                return 0
            if norm in {None, "*"}:
                return 1
            return 2

        def _language_bucket(raw_language: str | None) -> int:
            norm = _normalize_language(raw_language)
            if norm == language:
                return 0
            if norm == "en":
                return 1
            if norm == "*":
                return 2
            return 3

        ranked = sorted(
            values,
            key=lambda row: (
                _language_bucket(row.language),
                _country_bucket(row.country_code),
                int(row.id),
            ),
        )
        return ranked[0] if ranked else None

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        try:
            return int(str(value).strip())
        except Exception:
            return None

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _audit(
        *,
        object_type: str,
        source: str,
        profile_id: int | None,
        text_count: int,
        language: str,
        country_code: str | None,
    ) -> None:
        if not settings.TEXT_PROFILE_AUDIT_ENABLED:
            return
        logger.info(
            "text_profile_resolve object_type=%s source=%s profile_id=%s text_count=%s language=%s country=%s",
            object_type,
            source,
            profile_id,
            text_count,
            language,
            country_code or "-",
        )
