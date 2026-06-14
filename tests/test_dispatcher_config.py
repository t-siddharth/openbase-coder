from __future__ import annotations

import json
from pathlib import Path

from openbase_coder_cli import dispatcher_config


def test_backend_model_uses_env_backend(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "dispatcher-config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend_models": {
                    "codex": {"dispatcher": "gpt-5.5", "super_agents": "gpt-5.5"},
                    "claude_code": {
                        "dispatcher": "sonnet",
                        "super_agents": "opus",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENBASE_CODING_BACKEND", "claude_code")

    assert dispatcher_config.dispatcher_model(config_path) == "sonnet"
    assert dispatcher_config.super_agents_model(config_path) == "opus"


def test_backend_model_uses_env_file_backend(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    config_path = tmp_path / "dispatcher-config.json"
    env_file.write_text("OPENBASE_CODING_BACKEND=openbase_cloud\n", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "backend_models": {
                    "codex": {"super_agents": "gpt-5.5"},
                    "openbase_cloud": {"super_agents": "openbase-codex"},
                },
                "super_agents_model": "legacy-model",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENBASE_CODING_BACKEND", raising=False)
    monkeypatch.delenv("OPENBASE_CODEX_BACKEND", raising=False)
    monkeypatch.setattr(dispatcher_config, "DEFAULT_ENV_FILE_PATH", env_file)

    assert dispatcher_config.super_agents_model(config_path) == "openbase-codex"


def test_super_agents_model_ignores_legacy_key(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = tmp_path / "dispatcher-config.json"
    config_path.write_text(
        json.dumps({"super_agents_model": "legacy-model"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENBASE_CODING_BACKEND", "claude_code")

    assert dispatcher_config.super_agents_model(config_path) is None
