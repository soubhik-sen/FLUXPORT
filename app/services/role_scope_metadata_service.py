from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

from sqlalchemy.orm import Session

from app.core.decision.role_scope_metadata import get_role_scope_metadata
from app.models.company_master import CompanyMaster
from app.models.customer_master import CustomerMaster
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.user_customer_link import UserCustomerLink
from app.models.user_partner_link import UserPartnerLink
from app.services.role_scope_policy_validator import validate_role_scope_policy_payload
from app.services.user_scope_service import resolve_union_scope_ids

_FORWARDER_CODES = {"FO", "FORWARDER"}
_SUPPLIER_CODES = {"SU", "SUPPLIER"}


@dataclass
class MetadataScopeDecision:
    allow: bool
    scope_by_field: dict[str, set[int]]
    matched_policy_id: str | None = None
    reason: str | None = None
    bypass: bool = False


def _normalize_tokens(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {
        str(value).strip().lower()
        for value in values
        if value is not None and str(value).strip()
    }


def _normalize_roles(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {
        str(value).strip().upper()
        for value in values
        if value is not None and str(value).strip()
    }


def _normalize_endpoint_path(path: str | None) -> str:
    if not path:
        return ""
    normalized = path.strip().lower().split("?", 1)[0]
    normalized = normalized.replace("_", "-")
    normalized = re.sub(r"/+", "/", normalized)
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def _method_matches(policy_method: str | None, actual_method: str | None) -> bool:
    if not policy_method:
        return True
    if not actual_method:
        return False
    return policy_method.strip().upper() == actual_method.strip().upper()


def _path_matches(policy_path: str | None, actual_path: str | None) -> bool:
    if not policy_path:
        return False
    normalized_policy = _normalize_endpoint_path(policy_path)
    normalized_actual = _normalize_endpoint_path(actual_path)
    if not normalized_actual:
        return False
    if any(ch in normalized_policy for ch in "*?[]"):
        return fnmatchcase(normalized_actual, normalized_policy)
    return normalized_policy == normalized_actual


def _endpoint_key_matches(pattern: str | None, endpoint_key: str | None) -> bool:
    if not pattern or not endpoint_key:
        return False
    lhs = pattern.strip().lower()
    rhs = endpoint_key.strip().lower()
    if lhs == rhs:
        return True
    if any(ch in lhs for ch in "*?[]"):
        return fnmatchcase(rhs, lhs)
    return False


def _match_policy(
    endpoint_policies: list[dict[str, Any]],
    *,
    endpoint_key: str | None,
    http_method: str | None,
    endpoint_path: str | None,
) -> dict[str, Any] | None:
    for policy in endpoint_policies:
        if not isinstance(policy, dict):
            continue
        if not policy.get("enabled", True):
            continue

        policy_method = policy.get("method")
        policy_path = policy.get("path")
        has_method_or_path = bool(policy_method) or bool(policy_path)
        if has_method_or_path:
            if _method_matches(policy_method, http_method) and _path_matches(
                policy_path, endpoint_path
            ):
                return policy
            # Method/path-aware policies should only match by method+path.
            # Avoid endpoint-key fallback here; otherwise the first policy
            # sharing the same endpoint key can shadow later method-specific
            # policies (e.g., GET vs POST variants).
            continue

        if _endpoint_key_matches(policy.get("endpoint"), endpoint_key):
            return policy

    return None


def _is_partner_role_match(role_code: str | None, role_name: str | None, target: str | None) -> bool:
    normalized_target = (target or "").strip().upper()
    if not normalized_target:
        return True

    code = (role_code or "").strip().upper()
    name = (role_name or "").strip().upper()
    if normalized_target in _SUPPLIER_CODES:
        return code in _SUPPLIER_CODES or name == "SUPPLIER"
    if normalized_target in _FORWARDER_CODES:
        return code in _FORWARDER_CODES or name == "FORWARDER"
    return code == normalized_target or name == normalized_target


def _resolve_ids_from_source(db: Session, *, user_email: str, source: str) -> set[int]:
    source_normalized = " ".join((source or "").strip().split())
    source_lower = source_normalized.lower()
    if not source_lower:
        return set()

    if source_lower.startswith("user_customer_link.customer_id"):
        rows = (
            db.query(UserCustomerLink.customer_id)
            .join(CustomerMaster, CustomerMaster.id == UserCustomerLink.customer_id)
            .filter(UserCustomerLink.user_email == user_email)
            .filter(UserCustomerLink.deletion_indicator == False)
            .filter(CustomerMaster.is_active == True)
            .all()
        )
        return {int(row[0]) for row in rows if row and row[0] is not None}

    if source_lower.startswith("user_customer_link.company_id"):
        rows = (
            db.query(CustomerMaster.company_id)
            .select_from(UserCustomerLink)
            .join(CustomerMaster, CustomerMaster.id == UserCustomerLink.customer_id)
            .join(CompanyMaster, CompanyMaster.id == CustomerMaster.company_id)
            .filter(UserCustomerLink.user_email == user_email)
            .filter(UserCustomerLink.deletion_indicator == False)
            .filter(CustomerMaster.is_active == True)
            .filter(CustomerMaster.company_id.isnot(None))
            .filter(CompanyMaster.is_active == True)
            .all()
        )
        return {int(row[0]) for row in rows if row and row[0] is not None}

    if source_lower.startswith("user_partner_link.partner_id"):
        partner_role_filter: str | None = None
        match = re.search(
            r"where\s+partner_role\s*=\s*['\"]?([A-Za-z0-9_\- ]+)['\"]?",
            source_normalized,
            flags=re.IGNORECASE,
        )
        if match:
            partner_role_filter = match.group(1).strip()

        rows = (
            db.query(
                UserPartnerLink.partner_id,
                PartnerRole.role_code,
                PartnerRole.role_name,
            )
            .join(PartnerMaster, PartnerMaster.id == UserPartnerLink.partner_id)
            .join(PartnerRole, PartnerRole.id == PartnerMaster.role_id)
            .filter(UserPartnerLink.user_email == user_email)
            .filter(UserPartnerLink.deletion_indicator == False)
            .all()
        )
        resolved: set[int] = set()
        for partner_id, role_code, role_name in rows:
            if partner_id is None:
                continue
            if _is_partner_role_match(role_code, role_name, partner_role_filter):
                resolved.add(int(partner_id))
        return resolved

    return set()


def _resolve_v2_scope_by_field(
    db: Session,
    *,
    user_email: str,
    role_names: set[str],
    role_scope_mapping: list[dict[str, Any]],
    scope_dimensions: set[str],
) -> dict[str, set[int]]:
    scope_by_field: dict[str, set[int]] = {}
    for mapping in role_scope_mapping:
        if not isinstance(mapping, dict):
            continue
        role = (mapping.get("role") or "").strip().upper()
        if role and role not in role_names:
            continue

        dimension = (mapping.get("dimension") or "").strip()
        if not dimension:
            continue
        if scope_dimensions and dimension not in scope_dimensions:
            continue

        source = (mapping.get("source") or "").strip()
        if not source:
            continue
        ids = _resolve_ids_from_source(db, user_email=user_email, source=source)
        if not ids:
            continue

        target_field = (mapping.get("target_field") or dimension).strip()
        if not target_field:
            continue

        bucket = scope_by_field.setdefault(target_field, set())
        bucket.update(ids)

    return scope_by_field


def _resolve_v2_decision(
    db: Session,
    *,
    metadata: dict[str, Any],
    user_email: str,
    endpoint_key: str | None,
    http_method: str | None,
    endpoint_path: str | None,
) -> MetadataScopeDecision:
    endpoint_policies = metadata.get("endpoint_policies") or []
    role_scope_mapping = metadata.get("role_scope_mapping") or []
    if not isinstance(endpoint_policies, list) or not isinstance(role_scope_mapping, list):
        return MetadataScopeDecision(allow=True, scope_by_field={}, reason="invalid_metadata")

    policy = _match_policy(
        endpoint_policies,
        endpoint_key=endpoint_key,
        http_method=http_method,
        endpoint_path=endpoint_path,
    )
    if not policy:
        return MetadataScopeDecision(allow=True, scope_by_field={}, reason="no_policy")

    policy_id = (policy.get("id") or "").strip() or None
    union_scope = resolve_union_scope_ids(db, user_email)
    role_names = set(union_scope.role_names)

    bypass_roles = _normalize_roles(policy.get("bypass_roles"))
    if bypass_roles and not role_names.isdisjoint(bypass_roles):
        return MetadataScopeDecision(
            allow=True,
            scope_by_field={},
            matched_policy_id=policy_id,
            reason="bypass_role",
            bypass=True,
        )

    allowed_roles_any = _normalize_roles(policy.get("allowed_roles_any"))
    if allowed_roles_any and role_names.isdisjoint(allowed_roles_any):
        return MetadataScopeDecision(
            allow=False,
            scope_by_field={},
            matched_policy_id=policy_id,
            reason="allowed_roles_any_failed",
        )

    required_roles_all = _normalize_roles(policy.get("required_roles_all"))
    if required_roles_all and not required_roles_all.issubset(role_names):
        return MetadataScopeDecision(
            allow=False,
            scope_by_field={},
            matched_policy_id=policy_id,
            reason="required_roles_all_failed",
        )

    scoped_validation_errors = validate_role_scope_policy_payload(
        {
            "endpoint_policies": [policy],
            "role_scope_mapping": role_scope_mapping,
        },
        required_endpoint_keys=None,
    )
    if scoped_validation_errors:
        return MetadataScopeDecision(
            allow=False,
            scope_by_field={},
            matched_policy_id=policy_id,
            reason="invalid_metadata_contract",
        )

    scope_mode = str(policy.get("scope_mode") or "union").strip().lower()
    if scope_mode != "union":
        return MetadataScopeDecision(
            allow=True,
            scope_by_field={},
            matched_policy_id=policy_id,
            reason=f"scope_mode_{scope_mode}",
        )

    scope_dimensions = {
        str(value).strip()
        for value in (policy.get("scope_dimensions") or [])
        if str(value).strip()
    }
    scope_by_field = _resolve_v2_scope_by_field(
        db,
        user_email=user_email,
        role_names=role_names,
        role_scope_mapping=role_scope_mapping,
        scope_dimensions=scope_dimensions,
    )
    if scope_dimensions and not scope_by_field:
        return MetadataScopeDecision(
            allow=False,
            scope_by_field={},
            matched_policy_id=policy_id,
            reason="empty_resolved_scope_for_scoped_endpoint",
        )

    return MetadataScopeDecision(
        allow=True,
        scope_by_field=scope_by_field,
        matched_policy_id=policy_id,
        reason="ok",
    )


# Backward-compatible v1 support for earlier source_filter metadata shape.
def _resolve_v1_dimension_maps(db: Session, user_email: str) -> dict[str, dict[str, Any]]:
    union_scope = resolve_union_scope_ids(db, user_email)

    partner_rows = (
        db.query(
            UserPartnerLink.partner_id,
            PartnerMaster.partner_identifier,
            PartnerRole.role_code,
        )
        .join(PartnerMaster, PartnerMaster.id == UserPartnerLink.partner_id)
        .join(PartnerRole, PartnerRole.id == PartnerMaster.role_id)
        .filter(UserPartnerLink.user_email == user_email)
        .filter(UserPartnerLink.deletion_indicator == False)
        .all()
    )

    forwarder_ids_by_code: dict[str, int] = {}
    supplier_ids_by_code: dict[str, int] = {}
    for partner_id, partner_identifier, role_code in partner_rows:
        if partner_id is None:
            continue
        code = (partner_identifier or "").strip()
        role_code_norm = (role_code or "").strip().upper()
        if role_code_norm in _FORWARDER_CODES and code:
            forwarder_ids_by_code[code.lower()] = int(partner_id)
        if role_code_norm in _SUPPLIER_CODES and code:
            supplier_ids_by_code[code.lower()] = int(partner_id)

    customer_rows = (
        db.query(UserCustomerLink.customer_id, CustomerMaster.customer_identifier)
        .join(CustomerMaster, CustomerMaster.id == UserCustomerLink.customer_id)
        .filter(UserCustomerLink.user_email == user_email)
        .filter(UserCustomerLink.deletion_indicator == False)
        .filter(CustomerMaster.is_active == True)
        .all()
    )
    customer_ids_by_code: dict[str, int] = {}
    for customer_id, customer_identifier in customer_rows:
        if customer_id is None:
            continue
        code = (customer_identifier or "").strip()
        if code:
            customer_ids_by_code[code.lower()] = int(customer_id)

    return {
        "role_name": {"roles": set(union_scope.role_names)},
        "forwarder_code": {
            "ids": set(union_scope.forwarder_partner_ids),
            "ids_by_code": forwarder_ids_by_code,
            "default_target_field": "forwarder_id",
        },
        "supplier_code": {
            "ids": set(union_scope.supplier_partner_ids),
            "ids_by_code": supplier_ids_by_code,
            "default_target_field": "vendor_id",
        },
        "customer_code": {
            "ids": set(union_scope.customer_ids),
            "ids_by_code": customer_ids_by_code,
            "default_target_field": "customer_id",
        },
    }


def _resolve_v1_decision(
    db: Session,
    *,
    metadata: dict[str, Any],
    user_email: str,
    endpoint_key: str | None,
) -> MetadataScopeDecision:
    endpoint_policies = metadata.get("endpoint_policies") or []
    if not isinstance(endpoint_policies, list):
        return MetadataScopeDecision(allow=True, scope_by_field={}, reason="invalid_metadata")

    policy = _match_policy(
        endpoint_policies,
        endpoint_key=endpoint_key,
        http_method=None,
        endpoint_path=None,
    )
    if not policy:
        return MetadataScopeDecision(allow=True, scope_by_field={}, reason="no_policy")

    source_filter = policy.get("source_filter") or {}
    clauses = source_filter.get("clauses") or []
    if not isinstance(clauses, list):
        return MetadataScopeDecision(allow=True, scope_by_field={}, reason="no_clauses")

    dimension_maps = _resolve_v1_dimension_maps(db, user_email)
    role_names = set(dimension_maps.get("role_name", {}).get("roles") or set())
    scope_by_field: dict[str, set[int]] = {}
    for clause in clauses:
        if not isinstance(clause, dict):
            continue
        if clause.get("enabled") is False:
            continue

        any_roles = _normalize_roles(clause.get("when_any_role"))
        if any_roles and role_names.isdisjoint(any_roles):
            continue
        all_roles = _normalize_roles(clause.get("when_all_roles"))
        if all_roles and not all_roles.issubset(role_names):
            continue

        dimension_name = str(clause.get("dimension") or "").strip()
        dimension_entry = dimension_maps.get(dimension_name, {})
        target_field = str(
            clause.get("target_field")
            or dimension_entry.get("default_target_field")
            or ""
        ).strip()
        if not target_field:
            continue

        ids = set(dimension_entry.get("ids") or set())
        ids_by_code: dict[str, int] = dimension_entry.get("ids_by_code") or {}

        include_values = _normalize_tokens(clause.get("include_values"))
        if include_values:
            ids = {ids_by_code[v] for v in include_values if v in ids_by_code}
        exclude_values = _normalize_tokens(clause.get("exclude_values"))
        if exclude_values and ids_by_code:
            ids -= {ids_by_code[v] for v in exclude_values if v in ids_by_code}
        if not ids:
            continue

        bucket = scope_by_field.setdefault(target_field, set())
        bucket.update(ids)

    return MetadataScopeDecision(allow=True, scope_by_field=scope_by_field, reason="ok")


def resolve_metadata_scope_decision(
    db: Session,
    *,
    user_email: str,
    endpoint_key: str | None,
    http_method: str | None,
    endpoint_path: str | None,
) -> MetadataScopeDecision:
    metadata = get_role_scope_metadata()
    if "role_scope_mapping" in metadata:
        return _resolve_v2_decision(
            db,
            metadata=metadata,
            user_email=user_email,
            endpoint_key=endpoint_key,
            http_method=http_method,
            endpoint_path=endpoint_path,
        )
    return _resolve_v1_decision(
        db,
        metadata=metadata,
        user_email=user_email,
        endpoint_key=endpoint_key,
    )


def resolve_metadata_scope_by_field(
    db: Session,
    *,
    user_email: str,
    endpoint_key: str | None,
    http_method: str | None = None,
    endpoint_path: str | None = None,
) -> dict[str, set[int]]:
    decision = resolve_metadata_scope_decision(
        db,
        user_email=user_email,
        endpoint_key=endpoint_key,
        http_method=http_method,
        endpoint_path=endpoint_path,
    )
    return decision.scope_by_field
