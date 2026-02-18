from __future__ import annotations

import re
from typing import Any

_FORWARDER_CODES = {"FO", "FORWARDER"}
_SUPPLIER_CODES = {"SU", "SUPPLIER"}

REQUIRED_BUSINESS_ENDPOINT_KEYS: frozenset[str] = frozenset(
    {
        "purchase_orders",
        "purchase_orders.create",
        "purchase_orders.initialization_data",
        "purchase_orders.schedule_lines_merge",
        "purchase_orders.text_profile.resolve",
        "purchase_orders.texts.update",
        "shipments.from_schedule_lines",
        "shipments.create",
        "shipments.text_profile.resolve",
        "shipments.list",
        "shipments.workspace",
        "shipments.read",
        "shipments.delete",
        "shipments.texts.update",
        "reports.po_to_group",
        "reports.visibility",
        "reports.metadata",
        "reports.visibility.metadata",
    }
)

BUYER_SCOPED_ENDPOINT_KEYS: frozenset[str] = frozenset(
    {
        "purchase_orders",
        "purchase_orders.create",
        "purchase_orders.initialization_data",
        "purchase_orders.schedule_lines_merge",
        "purchase_orders.text_profile.resolve",
        "purchase_orders.texts.update",
        "shipments.from_schedule_lines",
        "shipments.create",
        "shipments.text_profile.resolve",
        "shipments.list",
        "shipments.workspace",
        "shipments.read",
        "shipments.delete",
        "shipments.texts.update",
        "reports.po_to_group",
        "reports.visibility",
        "reports.metadata",
        "reports.visibility.metadata",
    }
)


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


def _normalize_dimensions(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {
        str(value).strip()
        for value in values
        if value is not None and str(value).strip()
    }


def _normalize_endpoint_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalized_source(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _parse_partner_role(source: str) -> str | None:
    match = re.search(
        r"where\s+partner_role\s*=\s*['\"]?([A-Za-z0-9_\- ]+)['\"]?",
        source,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    token = match.group(1).strip().upper()
    return token or None


def is_source_dimension_compatible(*, dimension: str, source: str) -> bool:
    dimension_value = str(dimension or "").strip()
    source_normalized = _normalized_source(source)
    source_lower = source_normalized.lower()

    if not dimension_value or not source_lower:
        return False

    if source_lower.startswith("user_customer_link.customer_id"):
        return dimension_value == "customer_id"

    if source_lower.startswith("user_customer_link.company_id"):
        return dimension_value == "company_id"

    if source_lower.startswith("user_partner_link.partner_id"):
        partner_role = _parse_partner_role(source_normalized)
        if partner_role in _SUPPLIER_CODES:
            return dimension_value == "vendor_id"
        if partner_role in _FORWARDER_CODES:
            return dimension_value == "forwarder_id"
        return dimension_value in {"vendor_id", "forwarder_id"}

    return False


def validate_role_scope_policy_payload(
    payload: dict[str, Any],
    *,
    required_endpoint_keys: set[str] | frozenset[str] | None = REQUIRED_BUSINESS_ENDPOINT_KEYS,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["Payload must be a JSON object."]

    endpoint_policies = payload.get("endpoint_policies")
    role_scope_mapping = payload.get("role_scope_mapping")
    if not isinstance(endpoint_policies, list):
        errors.append("endpoint_policies must be a list.")
        endpoint_policies = []
    if not isinstance(role_scope_mapping, list):
        errors.append("role_scope_mapping must be a list.")
        role_scope_mapping = []

    role_to_dimensions: dict[str, set[str]] = {}
    for idx, raw in enumerate(role_scope_mapping):
        if not isinstance(raw, dict):
            errors.append(f"role_scope_mapping[{idx}] must be an object.")
            continue
        role = str(raw.get("role") or "").strip().upper()
        dimension = str(raw.get("dimension") or "").strip()
        source = _normalized_source(raw.get("source"))

        if not role:
            errors.append(f"role_scope_mapping[{idx}] role is required.")
            continue
        if not dimension:
            errors.append(f"role_scope_mapping[{idx}] dimension is required.")
            continue
        if not source:
            errors.append(f"role_scope_mapping[{idx}] source is required.")
            continue
        if not is_source_dimension_compatible(dimension=dimension, source=source):
            errors.append(
                "role_scope_mapping[%s] incompatible source/dimension pair: "
                "dimension='%s', source='%s'."
                % (idx, dimension, source)
            )
            continue

        role_to_dimensions.setdefault(role, set()).add(dimension)

    enforce_business_coverage = required_endpoint_keys is not None

    if enforce_business_coverage:
        enabled_endpoint_keys = {
            _normalize_endpoint_key(raw.get("endpoint"))
            for raw in endpoint_policies
            if isinstance(raw, dict) and raw.get("enabled", True)
        }
        missing_keys = sorted(
            key for key in required_endpoint_keys if key not in enabled_endpoint_keys
        )
        if missing_keys:
            errors.append(
                "Missing required endpoint policies: %s."
                % ", ".join(missing_keys)
            )

    for idx, raw in enumerate(endpoint_policies):
        if not isinstance(raw, dict):
            errors.append(f"endpoint_policies[{idx}] must be an object.")
            continue
        if raw.get("enabled", True) is False:
            continue

        scope_mode = str(raw.get("scope_mode") or "union").strip().lower()
        if scope_mode != "union":
            continue

        scope_dimensions = _normalize_dimensions(raw.get("scope_dimensions"))
        if not scope_dimensions:
            continue

        policy_id = str(raw.get("id") or f"index:{idx}").strip()
        endpoint_key = _normalize_endpoint_key(raw.get("endpoint"))
        allowed_roles_any = _normalize_roles(raw.get("allowed_roles_any"))
        required_roles_all = _normalize_roles(raw.get("required_roles_all"))
        candidate_roles = (
            allowed_roles_any or required_roles_all or set(role_to_dimensions.keys())
        )

        if not candidate_roles:
            errors.append(
                f"Policy {policy_id} declares scoped dimensions but has no resolvable roles."
            )
            continue

        matching_roles = [
            role
            for role in sorted(candidate_roles)
            if role_to_dimensions.get(role, set()) & scope_dimensions
        ]
        if not matching_roles:
            errors.append(
                "Policy %s has scoped dimensions %s but no allowed role can resolve them."
                % (policy_id, sorted(scope_dimensions))
            )
            continue

        if (
            enforce_business_coverage
            and
            endpoint_key in BUYER_SCOPED_ENDPOINT_KEYS
            and "customer_id" not in scope_dimensions
        ):
            errors.append(
                "Policy %s (%s) must include customer_id in scope_dimensions."
                % (policy_id, endpoint_key or "unknown-endpoint")
            )

    return errors
