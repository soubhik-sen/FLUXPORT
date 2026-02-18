from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import request_identity as request_identity_module
from app.core.config import settings
from app.schemas.request_identity import RequestIdentity


class _FakeVerifier:
    def verify(self, token: str):
        if token == "ok-token":
            return {
                "sub": "auth0|u-1",
                "email": "jwt@example.com",
                "iss": "https://tenant.example.com/",
                "aud": "https://api.example.com",
                "iat": 1,
                "exp": 9999999999,
            }
        if token == "ok-token-ns-email":
            return {
                "sub": "auth0|u-2",
                "https://dev-ka5vqws3lsqv2l1u.us.auth0.com/email": "ns.jwt@example.com",
                "iss": "https://tenant.example.com/",
                "aud": "https://api.example.com",
                "iat": 1,
                "exp": 9999999999,
            }
        raise Exception("bad token")


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/whoami")
    def whoami(identity: RequestIdentity = Depends(request_identity_module.get_request_identity)):
        return {
            "email": identity.email,
            "source": identity.auth_source,
            "sub": identity.subject,
        }

    return app


def test_legacy_header_mode_uses_x_user_email(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    app = _build_app()
    with TestClient(app) as client:
        r = client.get("/whoami", headers={"X-User-Email": "legacy@example.com"})
        assert r.status_code == 200
        payload = r.json()
        assert payload["email"] == "legacy@example.com"
        assert payload["source"] == "legacy_header"


def test_legacy_header_mode_ignores_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(request_identity_module, "_get_verifier", lambda: _FakeVerifier())
    app = _build_app()
    with TestClient(app) as client:
        r = client.get(
            "/whoami",
            headers={
                "Authorization": "Bearer ok-token",
                "X-User-Email": "legacy@example.com",
            },
        )
        assert r.status_code == 200
        payload = r.json()
        assert payload["email"] == "legacy@example.com"
        assert payload["source"] == "legacy_header"


def test_jwt_only_mode_requires_bearer(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "jwt_only")
    app = _build_app()
    with TestClient(app) as client:
        r = client.get("/whoami")
        assert r.status_code == 401


def test_dual_mode_prefers_bearer(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "dual")
    monkeypatch.setattr(request_identity_module, "_get_verifier", lambda: _FakeVerifier())
    app = _build_app()
    with TestClient(app) as client:
        r = client.get(
            "/whoami",
            headers={
                "Authorization": "Bearer ok-token",
                "X-User-Email": "legacy@example.com",
            },
        )
        assert r.status_code == 200
        payload = r.json()
        assert payload["email"] == "jwt@example.com"
        assert payload["source"] == "jwt"


def test_jwt_email_extracted_from_namespaced_claim(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "jwt_only")
    monkeypatch.setattr(request_identity_module, "_get_verifier", lambda: _FakeVerifier())
    app = _build_app()
    with TestClient(app) as client:
        r = client.get(
            "/whoami",
            headers={"Authorization": "Bearer ok-token-ns-email"},
        )
        assert r.status_code == 200
        payload = r.json()
        assert payload["email"] == "ns.jwt@example.com"
        assert payload["source"] == "jwt"
