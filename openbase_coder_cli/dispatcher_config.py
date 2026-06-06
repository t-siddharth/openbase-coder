from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from openbase_coder_cli.cartesia_voice_catalog import (
    cartesia_voice_for_id,
)
from openbase_coder_cli.paths import CODEX_DISPATCHER_CONFIG_PATH

REASONING_EFFORTS = {"low", "medium", "high", "xhigh"}
DISPATCHER_REASONING_EFFORT_KEY = "dispatcher_reasoning_effort"
SUPER_AGENTS_REASONING_EFFORT_KEY = "super_agents_reasoning_effort"
DISPATCHER_VOICE_ID_KEY = "dispatcher_voice_id"
DISPATCHER_VOICE_NAME_KEY = "dispatcher_voice_name"
DEFAULT_DISPATCHER_VOICE_ID = "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
DEFAULT_DISPATCHER_VOICE_NAME = "Jacqueline"


def read_dispatcher_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or CODEX_DISPATCHER_CONFIG_PATH
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def dispatcher_reasoning_effort(path: Path | None = None) -> str | None:
    value = _reasoning_effort_for_key(DISPATCHER_REASONING_EFFORT_KEY, path)
    return value if isinstance(value, str) and value in REASONING_EFFORTS else None


def super_agents_reasoning_effort(path: Path | None = None) -> str | None:
    value = _reasoning_effort_for_key(SUPER_AGENTS_REASONING_EFFORT_KEY, path)
    return value if isinstance(value, str) and value in REASONING_EFFORTS else None


def set_dispatcher_reasoning_effort(value: str, path: Path | None = None) -> Path:
    return _set_reasoning_effort(DISPATCHER_REASONING_EFFORT_KEY, value, path)


def set_super_agents_reasoning_effort(value: str, path: Path | None = None) -> Path:
    return _set_reasoning_effort(SUPER_AGENTS_REASONING_EFFORT_KEY, value, path)


def dispatcher_voice(path: Path | None = None) -> dict[str, str]:
    payload = read_dispatcher_config(path)
    voice_id = _optional_str(payload.get(DISPATCHER_VOICE_ID_KEY)) or os.getenv(
        "CARTESIA_VOICE_ID",
        DEFAULT_DISPATCHER_VOICE_ID,
    )
    catalog_voice = cartesia_voice_for_id(voice_id)
    voice_name = (
        catalog_voice.name
        if catalog_voice is not None
        else _optional_str(payload.get(DISPATCHER_VOICE_NAME_KEY))
        or DEFAULT_DISPATCHER_VOICE_NAME
    )
    return {
        "id": voice_id,
        "name": voice_name,
    }


def set_dispatcher_voice(voice_id: str, path: Path | None = None) -> dict[str, str]:
    normalized = voice_id.strip()
    voice = cartesia_voice_for_id(normalized)
    if voice is None:
        raise ValueError("Dispatcher voice must be selected from the Cartesia catalog.")

    config_path = path or CODEX_DISPATCHER_CONFIG_PATH
    _write_dispatcher_config(
        {
            **read_dispatcher_config(config_path),
            DISPATCHER_VOICE_ID_KEY: voice.id,
            DISPATCHER_VOICE_NAME_KEY: voice.name,
        },
        config_path,
    )
    return {"id": voice.id, "name": voice.name}


def _reasoning_effort_for_key(key: str, path: Path | None = None) -> str | None:
    value = read_dispatcher_config(path).get(key)
    return value if isinstance(value, str) else None


def _set_reasoning_effort(key: str, value: str, path: Path | None = None) -> Path:
    if value not in REASONING_EFFORTS:
        allowed = ", ".join(sorted(REASONING_EFFORTS))
        raise ValueError(f"Reasoning effort must be one of: {allowed}.")

    config_path = path or CODEX_DISPATCHER_CONFIG_PATH
    payload = {**read_dispatcher_config(config_path), key: value}
    _write_dispatcher_config(payload, config_path)
    return config_path


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _write_dispatcher_config(payload: dict[str, Any], config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=config_path.parent, delete=False) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, config_path)
