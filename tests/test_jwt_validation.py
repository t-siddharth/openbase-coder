import asyncio
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from openbase_coder_cli.config.jwt_validation import InvalidTokenError, JWKSValidator


def _make_token(
    *,
    kid: str = "test-key",
    issuer: str = "https://app.openbase.cloud",
    audience: str = "openbase-coder-cli",
):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = kid
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "gabe@example.com",
            "iat": now,
            "exp": now + 3600,
            "iss": issuer,
            "aud": audience,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )
    return token, {"keys": [jwk]}


class _SyncResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _AsyncClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, timeout, headers):
        return _SyncResponse(self._payload)


def test_validate_accepts_valid_rs256_token(monkeypatch):
    token, jwks = _make_token()
    monkeypatch.setattr(
        "openbase_coder_cli.config.jwt_validation.httpx.get",
        lambda url, timeout, headers: _SyncResponse(jwks),
    )

    validator = JWKSValidator(
        "https://example.com/.well-known/jwks.json",
        expected_issuer="https://app.openbase.cloud",
        expected_audience="openbase-coder-cli",
    )

    claims = validator.validate(token)

    assert claims["sub"] == "user-123"
    assert claims["email"] == "gabe@example.com"


def test_validate_async_accepts_valid_rs256_token(monkeypatch):
    token, jwks = _make_token()
    monkeypatch.setattr(
        "openbase_coder_cli.config.jwt_validation.httpx.AsyncClient",
        lambda: _AsyncClient(jwks),
    )

    validator = JWKSValidator(
        "https://example.com/.well-known/jwks.json",
        expected_issuer="https://app.openbase.cloud",
        expected_audience="openbase-coder-cli",
    )

    claims = asyncio.run(validator.validate_async(token))

    assert claims["sub"] == "user-123"


def test_validate_rejects_unknown_kid(monkeypatch):
    token, jwks = _make_token(kid="real-key")
    jwks["keys"][0]["kid"] = "different-key"
    monkeypatch.setattr(
        "openbase_coder_cli.config.jwt_validation.httpx.get",
        lambda url, timeout, headers: _SyncResponse(jwks),
    )

    validator = JWKSValidator("https://example.com/.well-known/jwks.json")

    with pytest.raises(InvalidTokenError, match="Unknown key ID"):
        validator.validate(token)


def test_validate_rejects_wrong_audience(monkeypatch):
    token, jwks = _make_token(audience="expected-audience")
    monkeypatch.setattr(
        "openbase_coder_cli.config.jwt_validation.httpx.get",
        lambda url, timeout, headers: _SyncResponse(jwks),
    )

    validator = JWKSValidator(
        "https://example.com/.well-known/jwks.json",
        expected_audience="different-audience",
    )

    with pytest.raises(InvalidTokenError):
        validator.validate(token)
