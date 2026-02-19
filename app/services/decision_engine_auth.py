from __future__ import annotations

import logging
import threading
import time
from functools import lru_cache

import requests

from app.core.config import settings
from app.core.security.request_auth_context import get_current_bearer_token

logger = logging.getLogger(__name__)


class DecisionEngineAuthError(Exception):
    pass


class _Auth0M2MTokenProvider:
    def __init__(self) -> None:
        self._domain = (settings.AUTH0_DOMAIN or "").strip()
        self._audience = (settings.AUTH0_AUDIENCE or "").strip()
        self._client_id = (settings.AUTH0_M2M_CLIENT_ID or "").strip()
        self._client_secret = (settings.AUTH0_M2M_CLIENT_SECRET or "").strip()
        self._token_url = (settings.AUTH0_M2M_TOKEN_URL or self._derive_token_url()).strip()
        self._timeout_seconds = float(settings.AUTH0_M2M_TIMEOUT_SECONDS or 6.0)
        self._leeway_seconds = max(0, int(settings.AUTH0_M2M_TOKEN_LEEWAY_SECONDS or 60))

        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._expires_at_epoch_seconds: float = 0

    def is_configured(self) -> bool:
        return bool(
            self._token_url
            and self._audience
            and self._client_id
            and self._client_secret
        )

    def get_access_token(self) -> str:
        if not self.is_configured():
            raise DecisionEngineAuthError(
                "Auth0 M2M fallback is not configured (token_url/audience/client_id/client_secret)."
            )

        now = time.time()
        with self._lock:
            if self._access_token and (now + self._leeway_seconds) < self._expires_at_epoch_seconds:
                return self._access_token

            token, expires_in_seconds = self._request_new_token()
            self._access_token = token
            self._expires_at_epoch_seconds = now + max(1, expires_in_seconds)
            return token

    def _derive_token_url(self) -> str:
        if not self._domain:
            return ""
        domain = self._domain.strip().rstrip("/")
        if domain.startswith("http://") or domain.startswith("https://"):
            return f"{domain}/oauth/token"
        return f"https://{domain}/oauth/token"

    def _request_new_token(self) -> tuple[str, int]:
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "audience": self._audience,
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(
                self._token_url,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise DecisionEngineAuthError(f"Auth0 token request failed: {exc}") from exc

        if response.status_code >= 400:
            raise DecisionEngineAuthError(
                f"Auth0 token request failed with HTTP {response.status_code}"
            )

        try:
            token_payload = response.json()
        except ValueError as exc:
            raise DecisionEngineAuthError("Auth0 token endpoint returned invalid JSON.") from exc

        token = str(token_payload.get("access_token", "")).strip()
        if not token:
            raise DecisionEngineAuthError("Auth0 token response missing access_token.")

        expires_in_raw = token_payload.get("expires_in", 3600)
        try:
            expires_in = int(expires_in_raw)
        except Exception:
            expires_in = 3600
        return token, expires_in


@lru_cache(maxsize=1)
def _get_m2m_provider() -> _Auth0M2MTokenProvider:
    return _Auth0M2MTokenProvider()


def resolve_decision_engine_bearer_token() -> str | None:
    user_token = get_current_bearer_token()
    if user_token:
        return user_token

    provider = _get_m2m_provider()
    if not provider.is_configured():
        return None

    try:
        return provider.get_access_token()
    except DecisionEngineAuthError as exc:
        logger.warning("decision_engine_m2m_token_unavailable error=%s", exc)
        return None
