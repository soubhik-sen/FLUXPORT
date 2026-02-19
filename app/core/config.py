"""
Centralized runtime configuration for FLUXPORT.

This module intentionally keeps parsing simple and explicit because these
values are used by both API behavior and policy rollout controls.

Key compatibility rule:
- If `ROLE_SCOPE_POLICY_ENABLED=false`, the app preserves historical behavior
  based on `UNION_SCOPE_ENABLED` (union when true, legacy precedence when false).
"""

import os
from pathlib import Path

from pydantic import BaseModel


def _load_local_env_file() -> None:
    """
    Lightweight .env loader used to keep runtime behavior consistent even when
    the server is started without `--env-file`.

    Precedence:
    - Existing OS environment variables win.
    - .env fills only missing keys.
    """
    current = Path(__file__).resolve()
    project_root = current.parents[2]
    env_path = project_root / ".env"
    if not env_path.exists():
        return

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            os.environ.setdefault(key, value)
    except Exception:
        # Keep config import resilient even if .env has malformed lines.
        return


_load_local_env_file()


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value.strip())
    except Exception:
        return default


def _normalize_csv(value: str | None) -> str:
    if value is None:
        return ""
    parts = [p.strip() for p in value.split(",")]
    return ",".join(p for p in parts if p)


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except Exception:
        return default


class Settings(BaseModel):
    # Primary app database connection string.
    # Example: postgresql://user:pass@host:5432/dbname
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:0kpy04n0HoOIjYN9TOJGKzMP3tEZiuk7@dpg-d5jv5tt6ubrc7398ucg0-a.oregon-postgres.render.com/commexwise_1jak",
    )

    # External decision engine URL used by timeline/decision orchestration flows.
    # Keep this reachable from API runtime environment.
    DECISION_ENGINE_URL: str = os.getenv("DECISION_ENGINE_URL", "http://127.0.0.1:8111")

    # Legacy union-scope switch (pre-policy-framework behavior).
    # true  => union scope across applicable dimensions
    # false => legacy precedence scope (forwarder > supplier > customer)
    UNION_SCOPE_ENABLED: bool = _as_bool(os.getenv("UNION_SCOPE_ENABLED"), True)

    # Master toggle for the new role-scope policy framework.
    # false => bypass policy framework and preserve historical behavior via UNION_SCOPE_ENABLED
    # true  => use ROLE_SCOPE_POLICY_MODE + rollout controls below
    ROLE_SCOPE_POLICY_ENABLED: bool = _as_bool(
        os.getenv("ROLE_SCOPE_POLICY_ENABLED"), True
    )

    # Policy mode selector for scoped endpoint resolution:
    # - auto:           uses UNION_SCOPE_ENABLED to choose union vs legacy
    # - legacy:         always legacy precedence
    # - union:          always union scope
    # - union_metadata: union scope driven by metadata rules (with optional fallback)
    ROLE_SCOPE_POLICY_MODE: str = (
        os.getenv("ROLE_SCOPE_POLICY_MODE", "auto").strip().lower()
    )

    # Comma-separated endpoint key patterns where policy mode should apply.
    # Supports fnmatch-style wildcards, e.g.:
    #   purchase_orders,reports.*,shipments.from_schedule_lines
    # Empty means apply everywhere.
    ROLE_SCOPE_ROLLOUT_ENDPOINTS: str = _normalize_csv(
        os.getenv("ROLE_SCOPE_ROLLOUT_ENDPOINTS")
    )

    # Identifier mode for metadata policy rules.
    # Current implementation supports readable identifiers (e.g. partner/customer codes).
    # Reserved for future extension.
    ROLE_SCOPE_IDENTIFIER_MODE: str = (
        os.getenv("ROLE_SCOPE_IDENTIFIER_MODE", "readable").strip().lower()
    )

    # Optional JSON file path for role-scope metadata configuration.
    # Empty => use built-in metadata defaults.
    ROLE_SCOPE_METADATA_PATH: str = os.getenv("ROLE_SCOPE_METADATA_PATH", "").strip()

    # In union_metadata mode:
    # true  => if metadata yields no scope for an endpoint/user, fallback to union scope
    # false => no fallback (empty metadata result remains empty scope)
    ROLE_SCOPE_METADATA_FALLBACK_TO_UNION: bool = _as_bool(
        os.getenv("ROLE_SCOPE_METADATA_FALLBACK_TO_UNION"), True
    )

    # Audit logging controls for scope decisions.
    # Useful for debugging production behavior without code changes.
    ROLE_SCOPE_AUDIT_ENABLED: bool = _as_bool(
        os.getenv("ROLE_SCOPE_AUDIT_ENABLED"), False
    )
    # true => logs full resolved ID sets; false => logs only summary stats
    ROLE_SCOPE_AUDIT_VERBOSE: bool = _as_bool(
        os.getenv("ROLE_SCOPE_AUDIT_VERBOSE"), False
    )
    # Sampling ratio [0..1] for audit events when enabled.
    # 1.0 => log all, 0.1 => about 10%, 0 => disabled by sampling.
    ROLE_SCOPE_AUDIT_SAMPLE_RATE: float = _as_float(
        os.getenv("ROLE_SCOPE_AUDIT_SAMPLE_RATE"), 1.0
    )

    # Metadata framework master switch.
    # false => framework is inert (no router registration, no runtime behavior changes).
    # true  => admin APIs become available for DB-backed metadata lifecycle.
    METADATA_FRAMEWORK_ENABLED: bool = _as_bool(
        os.getenv("METADATA_FRAMEWORK_ENABLED"), False
    )

    # Metadata source strategy for framework consumers.
    # - assets: keep reading static JSON assets
    # - db:     read published payloads from metadata framework tables
    # This flag is for gradual migration; default keeps current behavior unchanged.
    METADATA_FRAMEWORK_READ_MODE: str = (
        os.getenv("METADATA_FRAMEWORK_READ_MODE", "assets").strip().lower()
    )

    # Cache TTL (seconds) for metadata framework readers.
    METADATA_FRAMEWORK_CACHE_TTL_SEC: int = _as_int(
        os.getenv("METADATA_FRAMEWORK_CACHE_TTL_SEC"), 60
    )

    # Text-profile framework rollout controls.
    # false => legacy text behavior only (text_master + doc_text/text_val)
    # true  => enable text profile resolve + runtime text persistence paths.
    TEXT_PROFILE_ENABLED: bool = _as_bool(
        os.getenv("TEXT_PROFILE_ENABLED"), False
    )

    # Text-profile resolve strategy:
    # - decision_then_db: call decision engine first, fallback to DB rules/profile map.
    # - db_only:          skip decision engine and resolve from DB only.
    TEXT_PROFILE_RESOLVE_MODE: str = (
        os.getenv("TEXT_PROFILE_RESOLVE_MODE", "decision_then_db").strip().lower()
    )

    # Workspace compatibility fallback:
    # true  => when no runtime po_text/shipment_text exists, use legacy text sources.
    # false => runtime tables are authoritative (empty when no runtime rows).
    TEXT_PROFILE_LEGACY_WORKSPACE_FALLBACK: bool = _as_bool(
        os.getenv("TEXT_PROFILE_LEGACY_WORKSPACE_FALLBACK"), True
    )

    # Audit logging for text profile resolution decisions.
    TEXT_PROFILE_AUDIT_ENABLED: bool = _as_bool(
        os.getenv("TEXT_PROFILE_AUDIT_ENABLED"), False
    )

    # Mass change cockpit switch:
    # false => mass change endpoints return 404 (feature dark).
    # true  => dataset listing/template/validate/submit endpoints enabled.
    MASS_CHANGE_ENABLED: bool = _as_bool(
        os.getenv("MASS_CHANGE_ENABLED"), True
    )

    # Dataset catalog used by mass change cockpit phase gating.
    MASS_CHANGE_DATASET_CATALOG_PATH: str = os.getenv(
        "MASS_CHANGE_DATASET_CATALOG_PATH",
        "app/core/decision/mass_change_dataset_catalog.default.json",
    ).strip()

    # Document edit locking framework:
    # true  => lock endpoints are available and lock lifecycle is active
    # false => lock endpoints can still be called but writes should not enforce locks
    DOCUMENT_EDIT_LOCK_ENABLED: bool = _as_bool(
        os.getenv("DOCUMENT_EDIT_LOCK_ENABLED"), True
    )
    # Lock TTL in seconds. Active lock expires if heartbeat does not renew within this window.
    DOCUMENT_EDIT_LOCK_TTL_SECONDS: int = _as_int(
        os.getenv("DOCUMENT_EDIT_LOCK_TTL_SECONDS"), 600
    )
    # Heartbeat cadence expected from clients in change mode.
    DOCUMENT_EDIT_LOCK_HEARTBEAT_SECONDS: int = _as_int(
        os.getenv("DOCUMENT_EDIT_LOCK_HEARTBEAT_SECONDS"), 60
    )
    # Write enforcement switch:
    # true  => workspace writes require valid X-Document-Lock-Token
    # false => writes bypass lock token checks (useful for phased rollout)
    DOCUMENT_EDIT_LOCK_ENFORCE_WRITES: bool = _as_bool(
        os.getenv("DOCUMENT_EDIT_LOCK_ENFORCE_WRITES"), True
    )

    # Authentication mode:
    # - legacy_header: trust historical X-User-Email/X-User header identity.
    # - dual: prefer Bearer JWT, fallback to legacy header when token is absent.
    # - jwt_only: require valid Bearer JWT for protected identity resolution.
    AUTH_MODE: str = os.getenv("AUTH_MODE", "legacy_header").strip().lower()

    # Auth0 issuer domain, e.g. "tenant.us.auth0.com".
    AUTH0_DOMAIN: str = os.getenv("AUTH0_DOMAIN", "").strip()
    # Auth0 API audience (must match access token aud claim).
    AUTH0_AUDIENCE: str = os.getenv("AUTH0_AUDIENCE", "").strip()
    # Optional explicit issuer override.
    # If empty and AUTH0_DOMAIN is provided, defaults to "https://<domain>/".
    AUTH0_ISSUER: str = os.getenv("AUTH0_ISSUER", "").strip()
    # Optional explicit JWKS URI override.
    # If empty and AUTH0_DOMAIN is provided, defaults to
    # "https://<domain>/.well-known/jwks.json".
    AUTH0_JWKS_URI: str = os.getenv("AUTH0_JWKS_URI", "").strip()

    # JWT verification options.
    AUTH_JWT_ALGORITHMS: str = _normalize_csv(
        os.getenv("AUTH_JWT_ALGORITHMS") or "RS256"
    )
    AUTH_JWT_CLOCK_SKEW_SEC: int = _as_int(
        os.getenv("AUTH_JWT_CLOCK_SKEW_SEC"), 60
    )
    AUTH_JWKS_CACHE_TTL_SEC: int = _as_int(
        os.getenv("AUTH_JWKS_CACHE_TTL_SEC"), 300
    )
    AUTH_JWKS_TIMEOUT_SEC: int = _as_int(
        os.getenv("AUTH_JWKS_TIMEOUT_SEC"), 5
    )
    # Optional switch for local-only testing to bypass signature checks.
    AUTH_ALLOW_INSECURE_DEV_TOKENS: bool = _as_bool(
        os.getenv("AUTH_ALLOW_INSECURE_DEV_TOKENS"), False
    )

    # Auth0 M2M fallback credentials for backend-to-backend calls
    # when no request-scoped user bearer token is available.
    AUTH0_M2M_CLIENT_ID: str = (
        os.getenv("AUTH0_M2M_CLIENT_ID")
        or os.getenv("AUTH0_CLIENT_ID")
        or ""
    ).strip()
    AUTH0_M2M_CLIENT_SECRET: str = (
        os.getenv("AUTH0_M2M_CLIENT_SECRET")
        or os.getenv("AUTH0_CLIENT_SECRET")
        or ""
    ).strip()
    AUTH0_M2M_TOKEN_URL: str = os.getenv("AUTH0_M2M_TOKEN_URL", "").strip()
    AUTH0_M2M_TIMEOUT_SECONDS: float = _as_float(
        os.getenv("AUTH0_M2M_TIMEOUT_SECONDS"), 6.0
    )
    AUTH0_M2M_TOKEN_LEEWAY_SECONDS: int = _as_int(
        os.getenv("AUTH0_M2M_TOKEN_LEEWAY_SECONDS"), 60
    )

    # PO-create permission guard.
    # Comma-separated permission action keys that satisfy PO create authorization.
    # Example: "pocreate,create"
    PO_CREATE_PERMISSION_ACTION_KEYS: str = _normalize_csv(
        os.getenv("PO_CREATE_PERMISSION_ACTION_KEYS") or "pocreate"
    )
    # Comma-separated object types that pair with action keys above.
    # Example: "PO,PURCHASE_ORDER"
    PO_CREATE_PERMISSION_OBJECT_TYPES: str = _normalize_csv(
        os.getenv("PO_CREATE_PERMISSION_OBJECT_TYPES") or "PO"
    )

settings = Settings()
