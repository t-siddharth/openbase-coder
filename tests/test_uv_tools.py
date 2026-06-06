from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from openbase_coder_cli.services import uv_tools


def _write_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def test_resolve_uv_binary_prefers_workspace_virtualenv(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    uv_path = workspace / "cli" / ".venv" / "bin" / "uv"
    _write_executable(uv_path)

    monkeypatch.setattr(
        uv_tools.InstallationConfig,
        "exists",
        classmethod(lambda cls: True),
    )
    monkeypatch.setattr(
        uv_tools.InstallationConfig,
        "load",
        classmethod(
            lambda cls: SimpleNamespace(
                workspace_path=str(workspace),
            )
        ),
    )
    monkeypatch.setattr(uv_tools.shutil, "which", lambda name: None)

    assert uv_tools._resolve_uv_binary() == str(uv_path)  # noqa: SLF001


def test_resolve_uv_binary_uses_user_local_bin_when_path_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    uv_path = tmp_path / ".local" / "bin" / "uv"
    _write_executable(uv_path)

    monkeypatch.setattr(
        uv_tools.InstallationConfig,
        "exists",
        classmethod(lambda cls: False),
    )
    monkeypatch.setattr(uv_tools.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(uv_tools.shutil, "which", lambda name: None)

    assert uv_tools._resolve_uv_binary() == str(uv_path)  # noqa: SLF001


def test_uv_tool_help_runs_listed_executable_with_help(
    tmp_path: Path, monkeypatch
) -> None:
    executable_path = tmp_path / "bin" / "example"
    _write_executable(executable_path)
    monkeypatch.setattr(
        uv_tools,
        "list_uv_tools_payload",
        lambda: {
            "uv_available": True,
            "uv_path": "/usr/bin/uv",
            "tools": [
                {
                    "name": "example",
                    "executables": [
                        {"name": "example", "path": str(executable_path)},
                    ],
                }
            ],
            "error": None,
        },
    )

    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="usage", stderr="")

    monkeypatch.setattr(uv_tools.subprocess, "run", fake_run)

    payload, status_code = uv_tools.uv_tool_help_payload("example", "example")

    assert status_code == 200
    assert calls[0][0] == [str(executable_path), "--help"]
    assert calls[0][1]["timeout"] == 15
    assert payload["stdout"] == "usage"
    assert payload["return_code"] == 0


def test_uv_tool_help_rejects_unlisted_executable(tmp_path: Path, monkeypatch) -> None:
    executable_path = tmp_path / "bin" / "example"
    _write_executable(executable_path)
    monkeypatch.setattr(
        uv_tools,
        "list_uv_tools_payload",
        lambda: {
            "uv_available": True,
            "uv_path": "/usr/bin/uv",
            "tools": [
                {
                    "name": "example",
                    "executables": [
                        {"name": "example", "path": str(executable_path)},
                    ],
                }
            ],
            "error": None,
        },
    )

    payload, status_code = uv_tools.uv_tool_help_payload("example", "other")

    assert status_code == 404
    assert payload["error"] == "executable not found for uv tool example: other"
