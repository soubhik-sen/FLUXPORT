from __future__ import annotations

from app.api.deps import request_identity as request_identity_module
from app.core.config import settings


class _FakeVerifier:
    def verify(self, token: str):
        if token == "good-token":
            return {
                "sub": "auth0|seed-user",
                "email": "seed@example.com",
                "iss": "https://tenant.example.com/",
                "aud": "https://api.example.com",
                "iat": 1,
                "exp": 9999999999,
            }
        raise ValueError("invalid token")


def test_jwt_only_blocks_request_without_bearer(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "jwt_only")
    request_identity_module._get_verifier.cache_clear()
    response = client.get("/api/v1/purchase-orders/")
    assert response.status_code == 401


def test_jwt_only_allows_request_with_valid_bearer(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "jwt_only")
    monkeypatch.setattr(request_identity_module, "_get_verifier", lambda: _FakeVerifier())
    response = client.get(
        "/api/v1/purchase-orders/",
        headers={"Authorization": "Bearer good-token"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_jwt_only_blocks_non_v1_router_without_bearer(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "jwt_only")
    request_identity_module._get_verifier.cache_clear()
    response = client.get("/users")
    assert response.status_code == 401


def test_jwt_only_allows_non_v1_router_with_valid_bearer(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "jwt_only")
    monkeypatch.setattr(request_identity_module, "_get_verifier", lambda: _FakeVerifier())
    response = client.get(
        "/users",
        headers={"Authorization": "Bearer good-token"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
