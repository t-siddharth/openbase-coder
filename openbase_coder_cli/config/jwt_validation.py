"""Shared JWT validation using JWKS (RS256)."""

from __future__ import annotations

import logging
import time
from json import JSONDecodeError

import httpx
import jwt
from jwt import PyJWK, PyJWKSet

logger = logging.getLogger(__name__)

InvalidTokenError = jwt.InvalidTokenError


class JWKSValidator:
    """Validate RS256 JWTs against a remote JWKS endpoint."""

    def __init__(
        self,
        jwks_url: str,
        *,
        expected_issuer: str | None = None,
        expected_audience: str | None = None,
        cache_ttl: int = 3600,
    ) -> None:
        self._jwks_url = jwks_url
        self._expected_issuer = expected_issuer.rstrip("/") if expected_issuer else None
        self._expected_audience = expected_audience
        self._cache_ttl = cache_ttl
        self._keys: dict[str, PyJWK] = {}
        self._last_fetch = 0.0

    def _needs_refresh(self) -> bool:
        return time.time() - self._last_fetch > self._cache_ttl

    def _jwks_request_kwargs(self) -> dict[str, object]:
        return {
            "timeout": 10,
            "headers": {"Accept": "application/json"},
        }

    def _load_jwks_payload(self, jwks_data: object) -> None:
        if not isinstance(jwks_data, dict) or not isinstance(jwks_data.get("keys"), list):
            raise jwt.InvalidTokenError(
                f"JWKS endpoint returned invalid payload: {self._jwks_url}"
            )

        keyset = PyJWKSet.from_dict(jwks_data)
        self._keys = {key.key_id: key for key in keyset.keys if key.key_id}
        self._last_fetch = time.time()
        logger.info("Fetched JWKS from %s (%d keys)", self._jwks_url, len(self._keys))

    def _load_jwks_response(self, response: httpx.Response) -> None:
        try:
            self._load_jwks_payload(response.json())
        except JSONDecodeError as exc:
            raise jwt.InvalidTokenError(
                f"JWKS endpoint did not return JSON: {self._jwks_url}"
            ) from exc

    def _fetch_jwks(self) -> None:
        try:
            response = httpx.get(self._jwks_url, **self._jwks_request_kwargs())
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise jwt.InvalidTokenError(
                f"Unable to fetch JWKS from {self._jwks_url}"
            ) from exc
        self._load_jwks_response(response)

    async def _fetch_jwks_async(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._jwks_url, **self._jwks_request_kwargs()
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise jwt.InvalidTokenError(
                f"Unable to fetch JWKS from {self._jwks_url}"
            ) from exc
        self._load_jwks_response(response)

    def _cached_key(self, kid: str) -> PyJWK:
        key = self._keys.get(kid)
        if key is None:
            raise jwt.InvalidTokenError(f"Unknown key ID: {kid}")
        return key

    def _get_key(self, kid: str) -> PyJWK:
        if self._needs_refresh() or kid not in self._keys:
            self._fetch_jwks()
        return self._cached_key(kid)

    async def _get_key_async(self, kid: str) -> PyJWK:
        if self._needs_refresh() or kid not in self._keys:
            await self._fetch_jwks_async()
        return self._cached_key(kid)

    def _decode_claims(self, token: str, key: PyJWK) -> dict:
        options = {
            "require": ["exp", "iat"],
            "verify_aud": bool(self._expected_audience),
            "verify_iss": bool(self._expected_issuer),
        }
        decode_kwargs: dict[str, object] = {
            "algorithms": ["RS256"],
            "options": options,
        }
        if self._expected_audience:
            decode_kwargs["audience"] = self._expected_audience
        if self._expected_issuer:
            decode_kwargs["issuer"] = self._expected_issuer

        return jwt.decode(token, key.key, **decode_kwargs)

    def validate(self, token: str) -> dict:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise jwt.InvalidTokenError("JWT header missing 'kid'")

        key = self._get_key(kid)
        return self._decode_claims(token, key)

    async def validate_async(self, token: str) -> dict:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise jwt.InvalidTokenError("JWT header missing 'kid'")

        key = await self._get_key_async(kid)
        return self._decode_claims(token, key)
