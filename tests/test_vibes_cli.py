from __future__ import annotations

import importlib
import stat

from click.testing import CliRunner

from openbase_coder_cli.cli import main

vibes_cli = importlib.import_module("openbase_coder_cli.cli.vibes")


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_vibes_link_posts_credentials_and_saves_token(monkeypatch, tmp_path):
    token_path = tmp_path / "brain_score_token"
    calls = []

    def fake_post(url, *, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse({"access_token": "secret-token-value"})

    monkeypatch.setenv("OPENBASE_BRAIN_SCORE_TOKEN_FILE", str(token_path))
    monkeypatch.setattr(vibes_cli.httpx, "post", fake_post)

    result = CliRunner().invoke(
        main,
        ["vibes", "link"],
        input="y\nuser@example.com\nsecret-password\n",
    )

    assert result.exit_code == 0
    assert calls == [
        {
            "url": "http://uat.api.getvibes.ai/api/v1/auth/login",
            "json": {"email": "user@example.com", "password": "secret-password"},
            "timeout": 30,
        }
    ]
    assert token_path.read_text(encoding="utf-8") == "secret-token-value\n"
    assert stat.S_IMODE(token_path.stat().st_mode) == 0o600
    assert "secret-password" not in result.output
    assert "secret-token-value" not in result.output
    assert "HTTP only" in result.output
    assert "without HTTPS/TLS" in result.output


def test_vibes_link_cancel_does_not_send_credentials(monkeypatch, tmp_path):
    token_path = tmp_path / "brain_score_token"
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse({"access_token": "secret-token-value"})

    monkeypatch.setenv("OPENBASE_BRAIN_SCORE_TOKEN_FILE", str(token_path))
    monkeypatch.setattr(vibes_cli.httpx, "post", fake_post)

    result = CliRunner().invoke(main, ["vibes", "link"], input="n\n")

    assert result.exit_code == 0
    assert calls == []
    assert not token_path.exists()
    assert "Canceled. No credentials were sent." in result.output
