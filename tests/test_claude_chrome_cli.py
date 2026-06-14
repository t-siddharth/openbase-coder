from __future__ import annotations

import importlib

import httpx
from click.testing import CliRunner

claude_chrome_cli = importlib.import_module("openbase_coder_cli.cli.claude_chrome")
local_server = importlib.import_module("openbase_coder_cli.cli.local_server")


class FakeTokenManager:
    def get_access_token(self) -> str:
        return "jwt.token.value"


class FakeCompanionClient:
    instances: list["FakeCompanionClient"] = []

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        FakeCompanionClient.instances.append(self)

    def ensure_running(self) -> None:
        self.calls.append(("ensure_running", None))

    def status(self) -> dict:
        self.calls.append(("status", None))
        return {"ok": True, "state": "off"}

    def start_claude_chrome(self, **kwargs) -> dict:
        self.calls.append(("start_claude_chrome", kwargs))
        return {"ok": True, "state": "chrome-controlling"}

    def steer_claude_chrome(self, instructions: str) -> dict:
        self.calls.append(("steer_claude_chrome", instructions))
        return {"ok": True, "state": "chrome-controlling"}

    def queue_claude_chrome(self, instructions: str) -> dict:
        self.calls.append(("queue_claude_chrome", instructions))
        return {"ok": True, "state": "chrome-controlling"}

    def abort_claude_chrome(self) -> dict:
        self.calls.append(("abort_claude_chrome", None))
        return {"ok": True, "state": "off"}


def test_start_resolves_companion_session_and_starts_chrome_control(monkeypatch):
    FakeCompanionClient.instances = []

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url == "http://127.0.0.1:7999/api/livekit-companion-session/"
        return httpx.Response(
            200,
            json={
                "roomUrl": "ws://localhost:7880",
                "companionToken": "token",
                "companionTokenExpiresAt": "2026-05-23T12:00:00Z",
            },
        )

    monkeypatch.setattr(local_server, "get_token_manager", lambda: FakeTokenManager())
    monkeypatch.setattr(local_server.httpx, "request", fake_request)
    monkeypatch.setattr(claude_chrome_cli, "CompanionClient", FakeCompanionClient)

    result = CliRunner().invoke(
        claude_chrome_cli.claude_chrome,
        [
            "start",
            "--url",
            "https://example.com",
            "--max-turns",
            "4",
            "--permission-mode",
            "auto",
            "--allowed-tool",
            "Bash(git status)",
            "inspect",
            "the",
            "page",
        ],
    )

    assert result.exit_code == 0
    client = FakeCompanionClient.instances[0]
    assert [name for name, _ in client.calls] == [
        "ensure_running",
        "status",
        "start_claude_chrome",
    ]
    assert client.calls[2][1]["session"]["roomUrl"] == "ws://localhost:7880"
    assert client.calls[2][1]["instructions"] == "inspect the page"
    assert client.calls[2][1]["target_url"] == "https://example.com"
    assert client.calls[2][1]["max_turns"] == 4
    assert client.calls[2][1]["permission_mode"] == "auto"
    assert client.calls[2][1]["allowed_tools"] == ["Bash(git status)"]
    assert client.calls[2][1]["chrome_use_default_profile"] is True


def test_steer_calls_companion(monkeypatch):
    FakeCompanionClient.instances = []
    monkeypatch.setattr(claude_chrome_cli, "CompanionClient", FakeCompanionClient)

    result = CliRunner().invoke(
        claude_chrome_cli.claude_chrome, ["steer", "try", "again"]
    )

    assert result.exit_code == 0
    assert FakeCompanionClient.instances[0].calls == [
        ("steer_claude_chrome", "try again")
    ]


def test_queue_calls_companion(monkeypatch):
    FakeCompanionClient.instances = []
    monkeypatch.setattr(claude_chrome_cli, "CompanionClient", FakeCompanionClient)

    result = CliRunner().invoke(
        claude_chrome_cli.claude_chrome, ["queue", "then", "summarize"]
    )

    assert result.exit_code == 0
    assert FakeCompanionClient.instances[0].calls == [
        ("queue_claude_chrome", "then summarize")
    ]


def test_abort_calls_companion(monkeypatch):
    FakeCompanionClient.instances = []
    monkeypatch.setattr(claude_chrome_cli, "CompanionClient", FakeCompanionClient)

    result = CliRunner().invoke(claude_chrome_cli.claude_chrome, ["abort"])

    assert result.exit_code == 0
    assert FakeCompanionClient.instances[0].calls == [("abort_claude_chrome", None)]
