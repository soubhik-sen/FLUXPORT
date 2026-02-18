from __future__ import annotations

import logging
import random
from fnmatch import fnmatchcase

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.role_scope_metadata_service import resolve_metadata_scope_decision
from app.services.user_scope_service import (
    resolve_legacy_precedence_scope_ids,
    resolve_union_scope_ids,
)

logger = logging.getLogger(__name__)

_ALLOWED_POLICY_MODES = {"auto", "legacy", "union", "union_metadata"}
_SCOPE_DENY_FIELD = "__deny__"
_SCOPE_DENY_REASON_FIELD = "__deny_reason__"
_SCOPE_DENY_REASON_CODES = {
    "blocked": 1,
    "empty_resolved_scope_for_scoped_endpoint": 2,
    "invalid_metadata_contract": 3,
}
_SCOPE_DENY_REASON_BY_CODE = {
    code: reason for reason, code in _SCOPE_DENY_REASON_CODES.items()
}


def _normalized_policy_mode() -> str:
    mode = (settings.ROLE_SCOPE_POLICY_MODE or "auto").strip().lower()
    if mode not in _ALLOWED_POLICY_MODES:
        return "auto"
    return mode


def _rollout_patterns() -> list[str]:
    raw_value = settings.ROLE_SCOPE_ROLLOUT_ENDPOINTS or ""
    return [token.strip().lower() for token in raw_value.split(",") if token.strip()]


def _endpoint_in_rollout(endpoint_key: str | None) -> bool:
    patterns = _rollout_patterns()
    if not patterns:
        return True
    if not endpoint_key:
        return False
    candidate = endpoint_key.strip().lower()
    return any(fnmatchcase(candidate, pattern) for pattern in patterns)


def _audit_sample_rate() -> float:
    rate = settings.ROLE_SCOPE_AUDIT_SAMPLE_RATE
    try:
        value = float(rate)
    except Exception:
        value = 1.0
    return max(0.0, min(1.0, value))


def _should_emit_audit_log() -> bool:
    if not settings.ROLE_SCOPE_AUDIT_ENABLED:
        return False
    sample_rate = _audit_sample_rate()
    if sample_rate <= 0:
        return False
    if sample_rate >= 1:
        return True
    return random.random() <= sample_rate


def _audit_scope_resolution(
    *,
    endpoint_key: str | None,
    user_email: str | None,
    mode: str,
    scope_by_field: dict[str, set[int]],
) -> None:
    if not _should_emit_audit_log():
        return

    scope_sizes = {field: len(ids) for field, ids in scope_by_field.items()}
    logger.info(
        "role_scope_decision endpoint=%s user=%s mode=%s scope_keys=%s scope_sizes=%s",
        endpoint_key or "-",
        user_email or "-",
        mode,
        sorted(scope_by_field.keys()),
        scope_sizes,
    )
    if settings.ROLE_SCOPE_AUDIT_VERBOSE:
        logger.info(
            "role_scope_decision_scope endpoint=%s user=%s scope=%s",
            endpoint_key or "-",
            user_email or "-",
            {field: sorted(ids) for field, ids in scope_by_field.items()},
        )


def _resolve_scope_mode(endpoint_key: str | None) -> str:
    if not settings.ROLE_SCOPE_POLICY_ENABLED:
        # Backward-compatible behavior when policy framework is switched off:
        # preserve legacy UNION_SCOPE_ENABLED semantics used before this module.
        return "union" if settings.UNION_SCOPE_ENABLED else "legacy"

    policy_mode = _normalized_policy_mode()
    if policy_mode == "legacy":
        return "legacy"
    if not _endpoint_in_rollout(endpoint_key):
        return "legacy"
    if policy_mode in {"union", "union_metadata"}:
        return policy_mode
    if settings.UNION_SCOPE_ENABLED:
        return "union"
    return "legacy"


def is_union_scope_enabled_for_endpoint(endpoint_key: str | None) -> bool:
    return _resolve_scope_mode(endpoint_key) in {"union", "union_metadata"}


def is_scope_denied(scope_by_field: dict[str, set[int]] | None) -> bool:
    if not scope_by_field:
        return False
    return bool(scope_by_field.get(_SCOPE_DENY_FIELD))


def scope_deny_detail(scope_by_field: dict[str, set[int]] | None) -> str:
    if not is_scope_denied(scope_by_field):
        return "Access denied by role-scope policy"
    reason_codes = scope_by_field.get(_SCOPE_DENY_REASON_FIELD) or set()
    reason = None
    if reason_codes:
        reason = _SCOPE_DENY_REASON_BY_CODE.get(next(iter(reason_codes)))

    if reason == "empty_resolved_scope_for_scoped_endpoint":
        return "Access denied by role-scope policy: empty resolved scope for scoped endpoint"
    if reason == "invalid_metadata_contract":
        return "Access denied by role-scope policy: invalid scoped metadata contract"
    return "Access denied by role-scope policy"


def sanitize_scope_by_field(scope_by_field: dict[str, set[int]] | None) -> dict[str, set[int]]:
    if not scope_by_field:
        return {}
    return {
        field_name: set(ids)
        for field_name, ids in scope_by_field.items()
        if field_name not in {_SCOPE_DENY_FIELD, _SCOPE_DENY_REASON_FIELD}
    }


def resolve_scope_by_field(
    db: Session,
    *,
    user_email: str | None,
    endpoint_key: str | None = None,
    http_method: str | None = None,
    endpoint_path: str | None = None,
) -> dict[str, set[int]]:
    if not user_email:
        return {}

    effective_mode = _resolve_scope_mode(endpoint_key)

    if effective_mode == "union":
        scope_by_field = resolve_union_scope_ids(db, user_email).field_to_ids()
        _audit_scope_resolution(
            endpoint_key=endpoint_key,
            user_email=user_email,
            mode="union",
            scope_by_field=scope_by_field,
        )
        return scope_by_field

    if effective_mode == "union_metadata":
        decision = resolve_metadata_scope_decision(
            db,
            user_email=user_email,
            endpoint_key=endpoint_key,
            http_method=http_method,
            endpoint_path=endpoint_path,
        )
        if not decision.allow:
            reason_key = decision.reason or "blocked"
            scope_by_field = {
                _SCOPE_DENY_FIELD: {1},
                _SCOPE_DENY_REASON_FIELD: {
                    _SCOPE_DENY_REASON_CODES.get(
                        reason_key, _SCOPE_DENY_REASON_CODES["blocked"]
                    )
                },
            }
            mode = f"union_metadata_deny:{decision.reason or 'blocked'}"
        elif not decision.scope_by_field and settings.ROLE_SCOPE_METADATA_FALLBACK_TO_UNION:
            scope_by_field = resolve_union_scope_ids(db, user_email).field_to_ids()
            mode = "union_metadata_fallback_union"
        else:
            scope_by_field = decision.scope_by_field
            mode = "union_metadata"
        _audit_scope_resolution(
            endpoint_key=endpoint_key,
            user_email=user_email,
            mode=mode,
            scope_by_field=scope_by_field,
        )
        return scope_by_field

    scope_by_field = resolve_legacy_precedence_scope_ids(db, user_email)
    _audit_scope_resolution(
        endpoint_key=endpoint_key,
        user_email=user_email,
        mode="legacy",
        scope_by_field=scope_by_field,
    )
    return scope_by_field
