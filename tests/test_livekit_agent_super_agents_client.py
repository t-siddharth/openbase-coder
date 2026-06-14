from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from openbase_coder_cli.livekit_agent.super_agents_client import (
    SuperAgentsLiveKitClient,
    _speech_text_from_progress,
)


class FakeSuperAgentsBackend:
    backend = "claude-agent-sdk"

    def __init__(self) -> None:
        self.started_threads: list[dict[str, Any]] = []
        self.started_turns: list[tuple[Any, dict[str, Any]]] = []
        self.progress_calls = 0
        self.permission_callback: Any | None = None

    def register_permission_callback(self, callback: Any) -> None:
        self.permission_callback = callback

    async def start_thread(self, input_data: dict[str, Any]) -> dict[str, Any]:
        self.started_threads.append(input_data)
        return {"threadId": "dispatcher-thread"}

    async def resume_by_label(self, input_data) -> dict[str, Any]:
        return {"threadId": input_data.thread_id}

    async def start_turn_by_label(
        self,
        input_data,
        turn_input: dict[str, Any],
    ) -> dict[str, Any]:
        self.started_turns.append((input_data, turn_input))
        return {"turnId": "turn-1"}

    async def steer_by_label(self, input_data, prompt: str) -> dict[str, Any]:
        return {"turnId": input_data.turn_id, "prompt": prompt}

    async def progress_by_label(self, input_data) -> dict[str, Any]:
        self.progress_calls += 1
        return {
            "status": "waiting",
            "threadId": input_data.thread_id,
            "turnId": input_data.turn_id,
            "lastUsefulMessage": "The dispatcher answer is ready.",
        }


class FakeCodexSuperAgentsBackend(FakeSuperAgentsBackend):
    backend = "codex"

    def __init__(self) -> None:
        super().__init__()
        self.started_direct_turns: list[dict[str, Any]] = []
        self.resumed_threads: list[dict[str, Any]] = []

    async def resume_thread(
        self,
        thread_id: str,
        *,
        label: str | None = None,
        agent_name: str | None = None,
        developer_instructions: str | None = None,
    ) -> dict[str, Any]:
        self.resumed_threads.append(
            {
                "thread_id": thread_id,
                "label": label,
                "agent_name": agent_name,
                "developer_instructions": developer_instructions,
            }
        )
        return {"threadId": thread_id}

    async def start_turn(self, turn_input: dict[str, Any]) -> dict[str, Any]:
        self.started_direct_turns.append(turn_input)
        return {"turnId": "direct-turn-1"}

    async def progress_by_label(self, input_data) -> dict[str, Any]:
        self.progress_calls += 1
        return {
            "status": "waiting",
            "threadId": input_data.thread_id,
            "turnId": input_data.turn_id,
            "summary": {
                "items": [
                    {
                        "type": "agentMessage",
                        "text": "The direct dispatcher answer is ready.",
                    }
                ]
            },
        }


@pytest.mark.asyncio
async def test_super_agents_livekit_client_creates_thread_and_turn_through_backend(
    tmp_path: Path,
) -> None:
    backend = FakeSuperAgentsBackend()
    state_path = tmp_path / "livekit-voice-route.json"
    config_path = tmp_path / "dispatcher-config.json"
    config_path.write_text(
        json.dumps({"super_agents_model": "opus"}),
        encoding="utf-8",
    )
    client = SuperAgentsLiveKitClient(
        cwd="/tmp/project",
        state_path=str(state_path),
        developer_instructions="dispatcher instructions",
        dispatcher_config_path=config_path,
        backend_client=backend,
    )

    thread_id = await client.prepare()
    result = await client.run_turn(
        "hello",
        developer_instructions="voice instructions",
    )

    assert thread_id == "dispatcher-thread"
    assert (
        json.loads(state_path.read_text(encoding="utf-8"))["dispatcher_thread_id"]
        == "dispatcher-thread"
    )
    assert backend.started_threads[0]["label"] == "dispatcher"
    assert backend.started_threads[0]["cwd"] == "/tmp/project"
    assert backend.started_threads[0]["model"] == "opus"
    assert backend.started_turns[0][0].thread_id == "dispatcher-thread"
    assert backend.started_turns[0][1]["prompt"] == "hello"
    assert backend.started_turns[0][1]["model"] == "opus"
    assert (
        "dispatcher instructions"
        in backend.started_turns[0][1]["developerInstructions"]
    )
    assert "voice instructions" in backend.started_turns[0][1]["developerInstructions"]
    assert result["_livekit_turn_id"] == "turn-1"
    assert result["_livekit_speech_text"] == "The dispatcher answer is ready."


@pytest.mark.asyncio
async def test_super_agents_livekit_client_starts_codex_turn_by_thread_id(
    tmp_path: Path,
) -> None:
    backend = FakeCodexSuperAgentsBackend()
    state_path = tmp_path / "livekit-voice-route.json"
    client = SuperAgentsLiveKitClient(
        cwd="/tmp/project",
        state_path=str(state_path),
        backend_client=backend,
    )

    result = await client.run_turn("hello")

    assert backend.started_turns == []
    assert backend.started_direct_turns[0]["threadId"] == "dispatcher-thread"
    assert backend.started_direct_turns[0]["prompt"] == "hello"
    assert result["_livekit_turn_id"] == "direct-turn-1"
    assert result["_livekit_speech_text"] == "The direct dispatcher answer is ready."


@pytest.mark.asyncio
async def test_super_agents_livekit_client_resumes_codex_thread_by_id(
    tmp_path: Path,
) -> None:
    backend = FakeCodexSuperAgentsBackend()
    state_path = tmp_path / "livekit-voice-route.json"
    state_path.write_text(
        json.dumps({"dispatcher_thread_id": "canonical-dispatcher-thread"}),
        encoding="utf-8",
    )
    client = SuperAgentsLiveKitClient(
        cwd="/tmp/project",
        state_path=str(state_path),
        initial_thread_id="stale-dispatcher-thread",
        backend_client=backend,
    )

    thread_id = await client.prepare()

    assert thread_id == "canonical-dispatcher-thread"
    assert backend.resumed_threads == [
        {
            "thread_id": "canonical-dispatcher-thread",
            "label": "dispatcher",
            "agent_name": None,
            "developer_instructions": "Super Agent thread name: dispatcher",
        }
    ]
    assert backend.started_threads == []
    assert (
        json.loads(state_path.read_text(encoding="utf-8"))["dispatcher_thread_id"]
        == "canonical-dispatcher-thread"
    )


def test_super_agents_livekit_client_answers_mcp_elicitations(tmp_path: Path) -> None:
    backend = FakeCodexSuperAgentsBackend()
    SuperAgentsLiveKitClient(
        cwd=str(tmp_path),
        state_path=str(tmp_path / "livekit-voice-route.json"),
        backend_client=backend,
    )

    assert backend.permission_callback is not None
    accepted = backend.permission_callback(
        SimpleNamespace(
            method="mcpServer/elicitation/request",
            params={"serverName": "super_agents"},
        )
    )
    declined = backend.permission_callback(
        SimpleNamespace(
            method="mcpServer/elicitation/request",
            params={"serverName": "chrome"},
        )
    )

    assert accepted == {"action": "accept", "content": None, "_meta": None}
    assert declined == {"action": "decline", "content": None, "_meta": None}


def test_speech_text_from_progress_uses_agent_message_text() -> None:
    progress = {
        "summary": {
            "items": [
                {
                    "type": "agentMessage",
                    "text": "Here is the useful answer.",
                }
            ]
        }
    }

    assert _speech_text_from_progress(progress) == "Here is the useful answer."


def test_speech_text_from_progress_ignores_turn_ids() -> None:
    progress = {
        "summary": {
            "lastUsefulMessage": "019edae2 e304 77a3 9ddb 470ed17e64f7.",
        },
        "turn": {
            "id": "019edae2-e304-77a3-9ddb-470ed17e64f7",
            "status": "completed",
        },
    }

    assert _speech_text_from_progress(progress) == ""


def test_speech_text_from_progress_ignores_user_message_text() -> None:
    progress = {
        "summary": {
            "items": [
                {
                    "type": "userMessage",
                    "content": [
                        {
                            "type": "text",
                            "text": "hey are you there",
                        }
                    ],
                }
            ],
            "lastUsefulMessage": "hey are you there",
        },
        "turn": {
            "items": [
                {
                    "type": "userMessage",
                    "content": [
                        {
                            "type": "text",
                            "text": "can you hear me",
                        }
                    ],
                }
            ]
        },
    }

    assert _speech_text_from_progress(progress) == ""
