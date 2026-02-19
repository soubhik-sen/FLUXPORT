from __future__ import annotations

from functools import lru_cache
import logging

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security.auth0_jwt_verifier import (
    Auth0JWTVerifier,
    AuthTokenValidationError,
)
from app.core.security.jwks_cache import JwksCache
from app.core.security.request_auth_context import set_current_bearer_token
from app.db.session import get_db
from app.schemas.request_identity import RequestIdentity
from app.services.identity_mapping_service import attach_internal_user_context

logger = logging.getLogger(__name__)


def _normalized_auth_mode() -> str:
    raw = (settings.AUTH_MODE or "legacy_header").strip().lower()
    if raw in {"legacy_header", "dual", "jwt_only"}:
        return raw
    return "legacy_header"


def _auth0_issuer() -> str:
    if settings.AUTH0_ISSUER:
        issuer = settings.AUTH0_ISSUER.strip()
        return issuer if issuer.endswith("/") else f"{issuer}/"
    domain = settings.AUTH0_DOMAIN.strip()
    if not domain:
        return ""
    return f"https://{domain}/"


def _auth0_jwks_uri() -> str:
    if settings.AUTH0_JWKS_URI:
        return settings.AUTH0_JWKS_URI.strip()
    domain = settings.AUTH0_DOMAIN.strip()
    if not domain:
        return ""
    return f"https://{domain}/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _get_verifier() -> Auth0JWTVerifier:
    algorithms = [
        token.strip().upper()
        for token in (settings.AUTH_JWT_ALGORITHMS or "RS256").split(",")
        if token.strip()
    ]
    return Auth0JWTVerifier(
        issuer=_auth0_issuer(),
        audience=settings.AUTH0_AUDIENCE,
        jwks_uri=_auth0_jwks_uri(),
        algorithms=algorithms or ["RS256"],
        jwks_cache=JwksCache(
            ttl_sec=settings.AUTH_JWKS_CACHE_TTL_SEC,
            timeout_sec=settings.AUTH_JWKS_TIMEOUT_SEC,
        ),
        leeway_sec=settings.AUTH_JWT_CLOCK_SKEW_SEC,
        allow_insecure_dev_tokens=settings.AUTH_ALLOW_INSECURE_DEV_TOKENS,
    )


def _extract_bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization") or ""
    prefix = "Bearer "
    if not header.startswith(prefix):
        return None
    token = header[len(prefix) :].strip()
    return token or None


def _identity_from_legacy_header(request: Request) -> RequestIdentity:
    email = (
        request.headers.get("X-User-Email")
        or request.headers.get("X-User")
        or "system@local"
    )
    return RequestIdentity(
        subject=None,
        email=(email or "").strip().lower() or None,
        auth_source="legacy_header",
        claims={},
    )


def _extract_email_from_claims(claims: dict) -> str | None:
    for key in ("email", "upn", "preferred_username", "username"):
        value = claims.get(key)
        if value is None:
            continue
        text = str(value).strip().lower()
        if text:
            return text
    # Support common namespaced custom claims from Auth0 Actions/Rules,
    # e.g. "https://tenant.example.com/email".
    for raw_key, raw_value in claims.items():
        key = str(raw_key).strip().lower()
        if not (key.endswith("/email") or key.endswith(":email") or key.endswith("_email")):
            continue
        if raw_value is None:
            continue
        text = str(raw_value).strip().lower()
        if text:
            return text
    return None


def _identity_from_token(token: str) -> RequestIdentity:
    try:
        claims = _get_verifier().verify(token)
    except AuthTokenValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    subject = claims.get("sub")
    subject_text = str(subject).strip() if subject is not None else None
    email = _extract_email_from_claims(claims)
    if not email:
        logger.warning(
            "jwt_identity_email_missing subject=%s claim_keys=%s",
            subject_text or "-",
            sorted(str(k) for k in claims.keys()),
        )
    return RequestIdentity(
        subject=subject_text or None,
        email=email,
        auth_source="jwt",
        claims=claims,
    )


def resolve_request_identity(request: Request) -> RequestIdentity:
    token = _extract_bearer_token(request)
    set_current_bearer_token(token)
    mode = _normalized_auth_mode()
    if mode == "legacy_header":
        return _identity_from_legacy_header(request)

    if mode == "jwt_only":
        if not token:
            raise HTTPException(status_code=401, detail="Missing Bearer access token.")
        return _identity_from_token(token)

    # dual mode: prefer JWT when present, otherwise fallback to legacy header.
    if token:
        return _identity_from_token(token)
    return _identity_from_legacy_header(request)


def get_request_identity(request: Request) -> RequestIdentity:
    return resolve_request_identity(request)


def get_request_identity_with_db(
    request: Request,
    db: Session = Depends(get_db),
) -> RequestIdentity:
    identity = resolve_request_identity(request)
    return attach_internal_user_context(db, identity=identity)


def get_request_email(request: Request) -> str:
    identity = resolve_request_identity(request)
    return identity.email or "system@local"
