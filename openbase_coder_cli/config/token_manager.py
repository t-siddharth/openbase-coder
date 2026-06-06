"""
Manage locally-stored JWT tokens for CLI-to-service authentication.

Handles loading/saving refresh tokens to ~/.openbase/auth.json and
refreshing access tokens from the web backend's allauth API.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from collections.abc import Generator
from typing import Any

import httpx

from openbase_coder_cli.paths import AUTH_JSON_PATH

logger = logging.getLogger(__name__)

# Refresh the access token 60 seconds before it expires
_REFRESH_MARGIN_SECONDS = 60
DEFAULT_OAUTH_CLIENT_ID = "openbase-coder-cli"
DEFAULT_OAUTH_REDIRECT_URI = "http://127.0.0.1:52807/oauth/callback"
DEFAULT_WEB_BACKEND_URL = "https://app.openbase.cloud"


class TokenManager:
    """Manages JWT access + refresh tokens stored on disk.

    Usage::

        mgr = TokenManager(web_backend_url="https://backend.example.com")
        mgr.load()
        token = mgr.get_access_token()  # auto-refreshes if needed
    """

    def __init__(self, web_backend_url: str):
        self._web_backend_url = web_backend_url.rstrip("/")
        self._access_token: str = ""
        self._refresh_token: str = ""
        self._access_expires_at: float = 0  # epoch seconds

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load tokens from disk (if present)."""
        if not AUTH_JSON_PATH.is_file():
            self._access_token = ""
            self._refresh_token = ""
            self._access_expires_at = 0
            return
        data = json.loads(AUTH_JSON_PATH.read_text())
        self._access_token = data.get("access_token", "")
        self._refresh_token = data.get("refresh_token", "")
        self._access_expires_at = data.get("access_expires_at", 0)

    def save(self) -> None:
        """Persist current tokens to disk."""
        AUTH_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUTH_JSON_PATH.write_text(
            json.dumps(
                {
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                    "access_expires_at": self._access_expires_at,
                },
                indent=2,
            )
        )
        # Restrict permissions to owner-only
        AUTH_JSON_PATH.chmod(0o600)

    def clear(self) -> None:
        """Remove stored tokens."""
        self._access_token = ""
        self._refresh_token = ""
        self._access_expires_at = 0
        if AUTH_JSON_PATH.is_file():
            AUTH_JSON_PATH.unlink()

    # ------------------------------------------------------------------
    # Token state
    # ------------------------------------------------------------------

    def store_tokens(
        self,
        *,
        access_token: str,
        refresh_token: str,
        expires_in: int = 300,
    ) -> None:
        """Store tokens received from authentication and persist to disk."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._access_expires_at = time.time() + expires_in
        self.save()

    @property
    def is_logged_in(self) -> bool:
        self.load()
        return bool(self._refresh_token)

    def _access_is_valid(self) -> bool:
        return bool(self._access_token) and time.time() < (
            self._access_expires_at - _REFRESH_MARGIN_SECONDS
        )

    # ------------------------------------------------------------------
    # Access token (with auto-refresh)
    # ------------------------------------------------------------------

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing from the backend if needed.

        Raises ``RuntimeError`` if no refresh token is available, or
        ``httpx.HTTPStatusError`` if the refresh call fails.
        """
        self.load()
        if self._access_is_valid():
            return self._access_token

        if not self._refresh_token:
            raise RuntimeError(
                "No refresh token available. Run 'openbase-coder login' first."
            )

        self._do_refresh()
        return self._access_token

    def _do_refresh(self) -> None:
        """Refresh the access token using the stored refresh token."""
        url = f"{self._web_backend_url}/_allauth/app/v1/tokens/refresh"
        resp = httpx.post(
            url,
            json={"refresh_token": self._refresh_token},
            timeout=15,
        )
        resp.raise_for_status()

        data = resp.json()
        meta = data.get("meta", {}) if isinstance(data, dict) else {}
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        self._access_token = (
            meta.get("access_token")
            or payload.get("access_token")
            or data.get("access_token", "")
        )
        # Some allauth versions return a new refresh token
        new_refresh = (
            meta.get("refresh_token")
            or payload.get("refresh_token")
            or data.get("refresh_token")
        )
        if new_refresh:
            self._refresh_token = new_refresh
        expires_in = (
            meta.get("access_token_expires_in")
            or payload.get("access_token_expires_in")
            or 300
        )
        self._access_expires_at = time.time() + expires_in
        self.save()
        logger.info("Refreshed JWT access token")

    @property
    def has_refresh_token(self) -> bool:
        self.load()
        return bool(self._refresh_token)

    def get_access_token_payload(self) -> dict[str, Any]:
        token = self.get_access_token()
        expires_in = max(0, int(self._access_expires_at - time.time()))
        return {
            "access_token": token,
            "access_token_expires_in": expires_in,
        }


class CloudAccessTokenAuth(httpx.Auth):
    """HTTPX auth helper that injects a fresh cloud JWT per request."""

    requires_request_body = True

    def __init__(self, manager: TokenManager):
        self._manager = manager

    def _apply(self, request: httpx.Request) -> None:
        token = self._manager.get_access_token()
        request.headers["Authorization"] = f"Bearer {token}"

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        self._apply(request)
        yield request

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        self._apply(request)
        yield request


def get_cloud_auth_headers(web_backend_url: str | None = None) -> dict[str, str]:
    token = get_token_manager(web_backend_url).get_access_token()
    return {"Authorization": f"Bearer {token}"}


def create_pkce_verifier() -> str:
    return secrets.token_urlsafe(64)


def create_pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_instance: TokenManager | None = None


def get_token_manager(web_backend_url: str | None = None) -> TokenManager:
    """Return the global TokenManager, creating it if necessary.

    ``web_backend_url`` is required on first call (or taken from Django
    settings when imported in the server context).
    """
    global _instance
    if _instance is not None:
        return _instance

    if web_backend_url is None:
        web_backend_url = os.environ.get(
            "OPENBASE_CODER_CLI_WEB_BACKEND_URL",
            DEFAULT_WEB_BACKEND_URL,
        ).strip()

    if web_backend_url is None or not web_backend_url:
        try:
            from django.conf import settings
        except Exception:
            settings = None
        if settings is not None:
            web_backend_url = getattr(settings, "WEB_BACKEND_URL", "")

    if not web_backend_url:
        raise RuntimeError(
            "WEB_BACKEND_URL is not configured. "
            "Set OPENBASE_CODER_CLI_WEB_BACKEND_URL in your environment."
        )

    _instance = TokenManager(web_backend_url)
    _instance.load()
    return _instance
