from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from jwt.algorithms import RSAAlgorithm
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.security.auth0_jwt_verifier import (
    Auth0JWTVerifier,
    AuthTokenValidationError,
)
from app.core.security.jwks_cache import JwksCache


class _StaticJwksCache(JwksCache):
    def __init__(self, key_by_kid: dict[str, dict]) -> None:
        super().__init__(ttl_sec=300, timeout_sec=1)
        self._key_by_kid = key_by_kid

    def get_key(self, jwks_uri: str, kid: str) -> dict | None:  # type: ignore[override]
        return self._key_by_kid.get(kid)


def _build_rs256_token(*, issuer: str, audience: str, kid: str) -> tuple[str, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "auth0|abc123",
        "email": "jwt.user@example.com",
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    token = jwt.encode(
        payload,
        key=private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )
    return token, jwk


def test_auth0_jwt_verifier_accepts_valid_rs256_token():
    issuer = "https://tenant.example.com/"
    audience = "https://api.example.com"
    kid = "kid-1"
    token, jwk = _build_rs256_token(issuer=issuer, audience=audience, kid=kid)
    verifier = Auth0JWTVerifier(
        issuer=issuer,
        audience=audience,
        jwks_uri="https://tenant.example.com/.well-known/jwks.json",
        algorithms=["RS256"],
        jwks_cache=_StaticJwksCache({kid: jwk}),
        leeway_sec=0,
    )

    claims = verifier.verify(token)
    assert claims["sub"] == "auth0|abc123"
    assert claims["email"] == "jwt.user@example.com"


def test_auth0_jwt_verifier_rejects_invalid_audience():
    issuer = "https://tenant.example.com/"
    audience = "https://api.example.com"
    kid = "kid-2"
    token, jwk = _build_rs256_token(issuer=issuer, audience=audience, kid=kid)
    verifier = Auth0JWTVerifier(
        issuer=issuer,
        audience="https://wrong-audience.example.com",
        jwks_uri="https://tenant.example.com/.well-known/jwks.json",
        algorithms=["RS256"],
        jwks_cache=_StaticJwksCache({kid: jwk}),
        leeway_sec=0,
    )

    with pytest.raises(AuthTokenValidationError):
        verifier.verify(token)
