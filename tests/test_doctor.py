import importlib
from types import SimpleNamespace

from click.testing import CliRunner

from openbase_coder_cli.cli.doctor import _check_livekit_client_credentials

doctor_cli = importlib.import_module("openbase_coder_cli.cli.doctor")


def _collect_credential_check(env):
    messages = []

    def warn(message):
        messages.append(("warn", message))

    def ok(message):
        messages.append(("ok", message))

    _check_livekit_client_credentials(env, warn, ok)
    return messages


def test_livekit_client_credential_check_warns_when_missing():
    messages = _collect_credential_check(
        {
            "LIVEKIT_API_KEY": "server-key",
            "LIVEKIT_API_SECRET": "server-secret",
        }
    )

    assert messages == [
        (
            "warn",
            "LiveKit client token credentials missing "
            "(LIVEKIT_CLIENT_API_KEY, LIVEKIT_CLIENT_API_SECRET): "
            "run 'openbase-coder setup' and restart services",
        )
    ]


def test_livekit_client_credential_check_warns_when_reusing_server_credentials():
    messages = _collect_credential_check(
        {
            "LIVEKIT_API_KEY": "same-key",
            "LIVEKIT_API_SECRET": "same-secret",
            "LIVEKIT_CLIENT_API_KEY": "same-key",
            "LIVEKIT_CLIENT_API_SECRET": "same-secret",
        }
    )

    assert messages == [
        (
            "warn",
            "LiveKit client token credentials reuse local server credentials "
            "(LIVEKIT_CLIENT_API_KEY, LIVEKIT_CLIENT_API_SECRET): "
            "run 'openbase-coder setup' and restart services",
        )
    ]


def test_livekit_client_credential_check_accepts_separate_credentials():
    messages = _collect_credential_check(
        {
            "LIVEKIT_API_KEY": "server-key",
            "LIVEKIT_API_SECRET": "server-secret",
            "LIVEKIT_CLIENT_API_KEY": "client-key",
            "LIVEKIT_CLIENT_API_SECRET": "client-secret",
        }
    )

    assert messages == [
        (
            "ok",
            "LiveKit client token credentials: set and separate from server credentials",
        )
    ]


def test_doctor_allows_optional_stopped_services(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENBASE_CODER_CLI_SECRET_KEY=x\n", encoding="utf-8")
    monkeypatch.setattr(doctor_cli.InstallationConfig, "exists", lambda: True)
    monkeypatch.setattr(
        doctor_cli,
        "SERVICES",
        [SimpleNamespace(name="codex-thread-device-sync", install_by_default=False)],
    )
    monkeypatch.setattr(
        doctor_cli,
        "launchctl_status",
        lambda _svc: {"installed": True, "pid": None, "last_exit_code": None},
    )
    monkeypatch.setattr(
        doctor_cli,
        "_get_listening_sockets",
        lambda: [("127.0.0.1", 7999), ("127.0.0.1", 7880)],
    )
    monkeypatch.setattr(doctor_cli, "DEFAULT_ENV_FILE_PATH", env_file)
    monkeypatch.setattr(
        doctor_cli,
        "_parse_env_file",
        lambda: {
            "OPENBASE_CODER_CLI_SECRET_KEY": "secret",
            "LIVEKIT_API_KEY": "server-key",
            "LIVEKIT_API_SECRET": "server-secret",
            "LIVEKIT_CLIENT_API_KEY": "client-key",
            "LIVEKIT_CLIENT_API_SECRET": "client-secret",
        },
    )
    monkeypatch.setattr(
        doctor_cli,
        "tailscale_serve_health",
        lambda: SimpleNamespace(
            tailscale_available=True,
            tailscale_running=True,
            host="mac.tailnet.ts.net",
            openbase_url="http://mac.tailnet.ts.net:18080",
            openbase_configured=True,
            livekit_configured=True,
            openbase_reachable=True,
            error=None,
        ),
    )

    result = CliRunner().invoke(doctor_cli.doctor)

    assert result.exit_code == 0, result.output
    assert "codex-thread-device-sync: optional (not running" in result.output
