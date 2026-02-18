from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


DEFAULT_ROLE_SCOPE_METADATA: dict[str, Any] = {
    "version": "2.0",
    "description": "Metadata-driven role scope policy configuration.",
    "endpoint_policies": [
        {
            "id": "POL-PO-LIST",
            "endpoint": "purchase_orders",
            "method": "GET",
            "path": "/api/v1/purchase_orders",
            "enabled": True,
            "allowed_roles_any": ["USER_PURCH_BUYER", "SUPPLIER", "FORWARDER"],
            "required_roles_all": [],
            "scope_mode": "union",
            "scope_dimensions": ["customer_id", "vendor_id", "forwarder_id"],
            "bypass_roles": ["ADMIN_ORG"],
        },
        {
            "id": "POL-REPORT-PO-GROUP",
            "endpoint": "reports.po_to_group",
            "method": "GET",
            "path": "/api/v1/reports/po_to_group/data",
            "enabled": True,
            "allowed_roles_any": ["USER_PURCH_BUYER", "SUPPLIER", "FORWARDER"],
            "required_roles_all": [],
            "scope_mode": "union",
            "scope_dimensions": ["customer_id", "vendor_id", "forwarder_id"],
            "bypass_roles": ["ADMIN_ORG"],
        },
        {
            "id": "POL-REPORT-VISIBILITY",
            "endpoint": "reports.visibility",
            "method": "GET",
            "path": "/api/v1/reports/procurement_end_to_end/data",
            "enabled": True,
            "allowed_roles_any": ["USER_PURCH_BUYER", "SUPPLIER", "FORWARDER"],
            "required_roles_all": [],
            "scope_mode": "union",
            "scope_dimensions": ["customer_id", "vendor_id", "forwarder_id"],
            "bypass_roles": ["ADMIN_ORG"],
        },
        {
            "id": "POL-SHIP-CREATE",
            "endpoint": "shipments.from_schedule_lines",
            "method": "POST",
            "path": "/api/v1/shipments/from-schedule-lines",
            "enabled": True,
            "allowed_roles_any": ["USER_PURCH_BUYER", "FORWARDER"],
            "required_roles_all": [],
            "scope_mode": "union",
            "scope_dimensions": ["customer_id", "forwarder_id"],
            "bypass_roles": ["ADMIN_ORG"],
        },
        {
            "id": "POL-USER-PARTNERS",
            "endpoint": "admin.user_partners",
            "path": "/user-partners*",
            "enabled": True,
            "allowed_roles_any": ["ADMIN_ORG"],
            "required_roles_all": [],
            "scope_mode": "union",
            "scope_dimensions": [],
            "bypass_roles": ["ADMIN_ORG"],
        },
        {
            "id": "POL-USER-CUSTOMERS",
            "endpoint": "admin.user_customers",
            "path": "/user-customers*",
            "enabled": True,
            "allowed_roles_any": ["ADMIN_ORG"],
            "required_roles_all": [],
            "scope_mode": "union",
            "scope_dimensions": [],
            "bypass_roles": ["ADMIN_ORG"],
        },
        {
            "id": "POL-CUSTOMER-FORWARDERS",
            "endpoint": "admin.customer_forwarders",
            "path": "/customer-forwarders*",
            "enabled": True,
            "allowed_roles_any": ["ADMIN_ORG", "FORWARDER"],
            "required_roles_all": [],
            "scope_mode": "union",
            "scope_dimensions": ["forwarder_id"],
            "bypass_roles": ["ADMIN_ORG"],
        },
    ],
    "role_scope_mapping": [
        {
            "role": "USER_PURCH_BUYER",
            "dimension": "customer_id",
            "source": "user_customer_link.customer_id",
        },
        {
            "role": "SUPPLIER",
            "dimension": "vendor_id",
            "source": "user_partner_link.partner_id where partner_role=SUPPLIER",
        },
        {
            "role": "FORWARDER",
            "dimension": "forwarder_id",
            "source": "user_partner_link.partner_id where partner_role=FORWARDER",
        },
    ],
}

_CACHE_LOCK = Lock()
_CACHE_VALUE: dict[str, Any] | None = None
_CACHE_SOURCE: str = ""
_CACHE_EXPIRES_AT: float = 0.0


def _cache_ttl_seconds() -> int:
    try:
        value = int(settings.METADATA_FRAMEWORK_CACHE_TTL_SEC)
    except Exception:
        value = 60
    return max(0, value)


def _normalized_read_mode() -> str:
    mode = (settings.METADATA_FRAMEWORK_READ_MODE or "assets").strip().lower()
    return mode if mode in {"assets", "db"} else "assets"


def _db_read_enabled() -> bool:
    return bool(settings.METADATA_FRAMEWORK_ENABLED) and _normalized_read_mode() == "db"


def _cache_get(source: str) -> dict[str, Any] | None:
    now = monotonic()
    with _CACHE_LOCK:
        if source != _CACHE_SOURCE:
            return None
        if now >= _CACHE_EXPIRES_AT:
            return None
        if _CACHE_VALUE is None:
            return None
        return copy.deepcopy(_CACHE_VALUE)


def _cache_put(source: str, value: dict[str, Any]) -> None:
    ttl = _cache_ttl_seconds()
    now = monotonic()
    with _CACHE_LOCK:
        global _CACHE_VALUE, _CACHE_SOURCE, _CACHE_EXPIRES_AT
        _CACHE_SOURCE = source
        _CACHE_VALUE = copy.deepcopy(value)
        _CACHE_EXPIRES_AT = now + ttl if ttl > 0 else now


def reset_role_scope_metadata_cache() -> None:
    with _CACHE_LOCK:
        global _CACHE_VALUE, _CACHE_SOURCE, _CACHE_EXPIRES_AT
        _CACHE_VALUE = None
        _CACHE_SOURCE = ""
        _CACHE_EXPIRES_AT = 0.0


def _load_metadata_from_file(path_value: str) -> dict[str, Any] | None:
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        logger.warning("role_scope_metadata_file_not_found path=%s", path_value)
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(
            "role_scope_metadata_file_invalid_json path=%s error=%s",
            path_value,
            str(exc),
        )
        return None
    if not isinstance(payload, dict):
        logger.warning(
            "role_scope_metadata_file_invalid_shape path=%s expected=dict",
            path_value,
        )
        return None
    return payload


def _load_metadata_from_db() -> dict[str, Any] | None:
    try:
        from app.db.session import SessionLocal
        from app.services.metadata_framework_service import MetadataFrameworkService
    except Exception as exc:
        logger.warning("role_scope_metadata_db_import_error error=%s", str(exc))
        return None

    try:
        with SessionLocal() as db:
            published = MetadataFrameworkService.get_published(db, "role_scope_policy")
    except Exception as exc:
        logger.warning("role_scope_metadata_db_read_error error=%s", str(exc))
        return None

    if published is None:
        logger.warning("role_scope_metadata_db_missing type_key=role_scope_policy")
        return None

    payload = published.payload
    if not isinstance(payload, dict):
        logger.warning(
            "role_scope_metadata_db_invalid_shape type_key=role_scope_policy version=%s",
            published.version_no,
        )
        return None

    logger.info(
        "role_scope_metadata_db_loaded type_key=role_scope_policy version=%s",
        published.version_no,
    )
    return payload


def get_role_scope_metadata() -> dict[str, Any]:
    if _db_read_enabled():
        cached_db = _cache_get("db")
        if cached_db is not None:
            return cached_db

        loaded_db = _load_metadata_from_db()
        if loaded_db is not None:
            _cache_put("db", loaded_db)
            return copy.deepcopy(loaded_db)

    configured_path = settings.ROLE_SCOPE_METADATA_PATH
    if configured_path:
        cache_key = f"file:{configured_path}"
        cached_file = _cache_get(cache_key)
        if cached_file is not None:
            return cached_file

        loaded = _load_metadata_from_file(configured_path)
        if loaded is not None:
            _cache_put(cache_key, loaded)
            return copy.deepcopy(loaded)

    cached_default = _cache_get("default")
    if cached_default is not None:
        return cached_default
    _cache_put("default", DEFAULT_ROLE_SCOPE_METADATA)
    return copy.deepcopy(DEFAULT_ROLE_SCOPE_METADATA)
