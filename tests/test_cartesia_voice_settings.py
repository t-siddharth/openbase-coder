from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OPENBASE_CODER_CLI_SECRET_KEY", "test-secret")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openbase_coder_cli.config.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

django.setup()

from openbase_coder_cli import dispatcher_config  # noqa: E402
from openbase_coder_cli.openbase_coder_cli_app import views  # noqa: E402


def _authenticated_request(method: str, path: str, data: dict | None = None):
    factory = APIRequestFactory()
    request_factory = factory.get if method == "GET" else factory.put
    request = request_factory(path, data=data or {}, format="json")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return request


def test_cartesia_voice_settings_returns_catalog_and_dispatcher_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "dispatcher-config.json"
    monkeypatch.setattr(dispatcher_config, "CODEX_DISPATCHER_CONFIG_PATH", config_path)
    monkeypatch.setattr(views, "dispatcher_voice", dispatcher_config.dispatcher_voice)

    response = views.cartesia_voice_settings(
        _authenticated_request("GET", "/api/settings/cartesia-voices/")
    )

    assert response.status_code == 200
    assert response.data["dispatcher_voice"] == {
        "id": "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        "name": "Jacqueline",
    }
    assert response.data["voices"][0]["name"] == "Jacqueline"
    assert any(voice["name"] == "Thandi" for voice in response.data["voices"])


def test_dispatcher_voice_settings_persists_verified_name(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "dispatcher-config.json"
    monkeypatch.setattr(dispatcher_config, "CODEX_DISPATCHER_CONFIG_PATH", config_path)
    monkeypatch.setattr(views, "set_dispatcher_voice", dispatcher_config.set_dispatcher_voice)

    response = views.dispatcher_voice_settings(
        _authenticated_request(
            "PUT",
            "/api/settings/dispatcher-voice/",
            {"voice_id": "692846ad-1a6b-49b8-bfc5-86421fd41a19"},
        )
    )

    assert response.status_code == 200
    assert response.data["dispatcher_voice"] == {
        "id": "692846ad-1a6b-49b8-bfc5-86421fd41a19",
        "name": "Thandi",
    }
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["dispatcher_voice_id"] == "692846ad-1a6b-49b8-bfc5-86421fd41a19"
    assert payload["dispatcher_voice_name"] == "Thandi"


def test_dispatcher_voice_settings_rejects_unknown_voice() -> None:
    response = views.dispatcher_voice_settings(
        _authenticated_request(
            "PUT",
            "/api/settings/dispatcher-voice/",
            {"voice_id": "unknown-voice"},
        )
    )

    assert response.status_code == 400
    assert "catalog" in response.data["detail"]
