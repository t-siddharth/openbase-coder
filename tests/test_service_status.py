from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("OPENBASE_CODER_CLI_SECRET_KEY", "test-secret")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openbase_coder_cli.config.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

django.setup()

from openbase_coder_cli.openbase_coder_cli_app import (  # noqa: E402
    services_views,
    views,
)


def test_service_status_includes_background_openbase_services(monkeypatch) -> None:
    monkeypatch.setattr(services_views, "_check_port", lambda port: True)
    monkeypatch.setattr(services_views, "_check_tailscale", lambda: True)
    monkeypatch.setattr(services_views, "_check_web_backend", lambda: True)

    def fake_launchctl_status(service):
        return {
            "installed": True,
            "pid": "123" if service.name == "codex-thread-sync" else None,
            "last_exit_code": None,
        }

    monkeypatch.setattr(services_views, "launchctl_status", fake_launchctl_status)

    request = APIRequestFactory().get("/api/status/")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))

    response = views.service_status(request)

    assert response.status_code == 200
    assert response.data["services"]["codex_thread_sync"] == {
        "name": "Codex Thread Sync",
        "port": None,
        "running": True,
        "installed": True,
        "last_exit_code": None,
    }
    assert response.data["services"]["openbase_routines"] == {
        "name": "Openbase Routines",
        "port": None,
        "running": False,
        "installed": True,
        "last_exit_code": None,
    }
    assert len(response.data["services"]) == 8
