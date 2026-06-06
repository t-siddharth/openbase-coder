"""JWT authentication backend for openbase_coder_cli."""

from __future__ import annotations

import logging

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from openbase_coder_cli.config.jwt_validation import InvalidTokenError, JWKSValidator
from rest_framework import authentication, exceptions

logger = logging.getLogger(__name__)

_validator: JWKSValidator | None = None


def _get_validator() -> JWKSValidator | None:
    """Lazily create the shared JWKS validator (if configured)."""
    global _validator
    if _validator is not None:
        return _validator

    web_backend_url = getattr(settings, "WEB_BACKEND_URL", "")
    if not web_backend_url:
        return None

    _validator = JWKSValidator(
        getattr(settings, "JWT_JWKS_URL", f"{web_backend_url}/.well-known/jwks.json"),
        expected_issuer=getattr(settings, "JWT_ISSUER", web_backend_url),
        expected_audience=getattr(settings, "JWT_AUDIENCE", "openbase-coder-cli"),
    )
    return _validator


def _validate_via_auth_session(token: str) -> dict:
    """Fallback validator using the backend auth/session endpoint."""
    web_backend_url = getattr(settings, "WEB_BACKEND_URL", "").rstrip("/")
    if not web_backend_url:
        raise InvalidTokenError("WEB_BACKEND_URL is not configured")

    session_url = getattr(
        settings, "JWT_AUTH_SESSION_URL", f"{web_backend_url}/_allauth/app/v1/auth/session"
    )
    try:
        resp = httpx.get(
            session_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise InvalidTokenError(
            f"Unable to validate JWT via auth session endpoint: {session_url}"
        ) from exc

    if resp.status_code != 200:
        raise InvalidTokenError(f"Auth session rejected token ({resp.status_code})")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise InvalidTokenError(
            f"Auth session endpoint returned non-JSON response: {session_url}"
        ) from exc

    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    if not meta.get("is_authenticated"):
        raise InvalidTokenError("Auth session reports unauthenticated token")

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    user_data = data.get("user", {}) if isinstance(data, dict) else {}
    sub = user_data.get("id") or user_data.get("email") or user_data.get("username")
    if not sub:
        raise InvalidTokenError("Auth session response missing user identity")

    claims = {"sub": str(sub)}
    if user_data.get("email"):
        claims["email"] = str(user_data["email"])
    return claims


def _get_or_create_user(*, sub: str):
    """Get or create a Django user from a JWT ``sub`` claim."""
    User = get_user_model()
    user = User.objects.filter(username=sub).first()
    if user is not None:
        return user

    email = f"{sub}@jwt"
    manager = User.objects

    if hasattr(manager, "create_user"):
        return manager.create_user(username=sub, email=email, password=None)

    user = User(username=sub, email=email)
    if hasattr(user, "set_unusable_password"):
        user.set_unusable_password()
    user.save()
    return user


class JWTAuthentication(authentication.BaseAuthentication):
    """Validate RS256 JWTs signed by the web backend.

    Falls through (returns None) when:
    - No Authorization header is present
    - The bearer token does not look like a JWT (no '.' separators)
    - WEB_BACKEND_URL is not configured
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request)
        if not auth_header:
            return None

        try:
            auth_parts = auth_header.decode("utf-8").split()
        except UnicodeDecodeError:
            return None

        if len(auth_parts) != 2 or auth_parts[0].lower() != self.keyword.lower():
            return None

        token = auth_parts[1]

        # Static bearer tokens don't contain '.'; JWTs have exactly two.
        if token.count(".") != 2:
            return None

        validator = _get_validator()
        if validator is None:
            return None

        try:
            claims = validator.validate(token)
        except InvalidTokenError as exc:
            logger.info("Local JWT validation failed; trying auth/session fallback: %s", exc)
            try:
                claims = _validate_via_auth_session(token)
            except InvalidTokenError:
                raise exceptions.AuthenticationFailed(str(exc)) from None

        user = _get_or_create_user(sub=claims["sub"])
        return (user, claims)

    def authenticate_header(self, request):
        return self.keyword
