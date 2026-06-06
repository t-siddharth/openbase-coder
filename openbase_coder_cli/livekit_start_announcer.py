from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from openbase_coder_cli.cli.utils import get_data_dir

logger = logging.getLogger(__name__)

ANNOUNCEMENT_STATE_FILE = "livekit-super-agent-announcements.json"


async def announce_super_agent_start(
    *,
    thread_id: str,
    turn_id: str,
    agent_name: str | None,
    issue: str,
) -> bool:
    if not thread_id or not turn_id:
        return False
    if _already_announced(turn_id):
        return False
    if not _has_livekit_voice_route():
        return False

    resolved_agent_name = _clean_agent_name(agent_name)
    if not resolved_agent_name:
        return False
    _record_announcement_voice(thread_id, resolved_agent_name)
    message = _announcement_text(resolved_agent_name, issue)
    for command in _announcement_commands():
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                "user",
                "say",
                resolved_agent_name,
                message,
                env=os.environ,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return_code = await process.wait()
        except OSError:
            continue
        if return_code == 0:
            _mark_announced(turn_id)
            return True

    logger.debug("Unable to announce Super Agent start turn_id=%s", turn_id)
    return False


def _announcement_text(agent_name: str | None, issue: str) -> str:
    name = _clean_agent_name(agent_name) or "Super Agent"
    normalized_issue = " ".join((issue or "").split()) or "the task"
    if len(normalized_issue) > 120:
        normalized_issue = normalized_issue[:117].rsplit(" ", 1)[0].strip() + "..."
    return f"Hello, my name is {name}, working on {normalized_issue}."


def _record_announcement_voice(thread_id: str, agent_name: str) -> None:
    try:
        from openbase_coder_cli.livekit_voice_history import record_voice_assignment
        from openbase_coder_cli.livekit_voice_route import super_agent_voice_for_context

        voice = super_agent_voice_for_context(thread_id, None, agent_name)
        record_voice_assignment(
            thread_id=thread_id,
            agent_name=agent_name,
            cwd=None,
            voice_id=voice.voice_id if voice else None,
            voice_name=voice.name if voice else None,
            kind="codex_thread",
            source="super_agent_announcement",
        )
    except Exception:
        logger.debug("Unable to record Super Agent announcement voice", exc_info=True)


def _announcement_commands() -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = []
    venv_command = Path(sys.executable).with_name("openbase-coder")
    if venv_command.is_file():
        commands.append((str(venv_command),))
    fallback = shutil.which("openbase-coder") or "openbase-coder"
    if fallback != str(venv_command):
        commands.append((fallback,))
    return commands


def _has_livekit_voice_route() -> bool:
    try:
        from openbase_coder_cli.livekit_voice_route import get_livekit_voice_route_state

        state = get_livekit_voice_route_state()
    except Exception:
        return False
    return bool(state.dispatcher_thread_id or state.active_target_thread_id)


def _already_announced(turn_id: str) -> bool:
    return turn_id in _read_state().get("turn_ids", [])


def _mark_announced(turn_id: str) -> None:
    state = _read_state()
    turn_ids = [
        candidate
        for candidate in state.get("turn_ids", [])
        if isinstance(candidate, str) and candidate
    ]
    if turn_id not in turn_ids:
        turn_ids.append(turn_id)
    state["turn_ids"] = turn_ids[-500:]
    state["updated_at"] = time.time()
    _write_state(state)


def _state_path() -> Path:
    return get_data_dir() / ANNOUNCEMENT_STATE_FILE


def _read_state() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return {"turn_ids": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"turn_ids": []}
    return payload if isinstance(payload, dict) else {"turn_ids": []}


def _write_state(payload: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _clean_agent_name(value: str | None) -> str | None:
    return " ".join(value.split()) if isinstance(value, str) and value.split() else None
