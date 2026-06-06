from __future__ import annotations

import asyncio

from openbase_coder_cli import livekit_start_announcer


def test_announce_super_agent_start_uses_explicit_agent_name(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENBASE_CODER_CLI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(livekit_start_announcer, "_has_livekit_voice_route", lambda: True)
    monkeypatch.setattr(livekit_start_announcer, "_announcement_commands", lambda: [("openbase-coder",)])

    recorded = []
    calls = []

    def fake_record(thread_id: str, agent_name: str) -> None:
        recorded.append((thread_id, agent_name))

    class FakeProcess:
        async def wait(self):
            return 0

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr(livekit_start_announcer, "_record_announcement_voice", fake_record)
    monkeypatch.setattr(
        livekit_start_announcer.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    announced = asyncio.run(
        livekit_start_announcer.announce_super_agent_start(
            thread_id="thread-1",
            turn_id="turn-1",
            agent_name="Dottie",
            issue="Inspect repo",
        )
    )

    assert announced is True
    assert recorded == [("thread-1", "Dottie")]
    assert calls[0][0][:4] == ("openbase-coder", "user", "say", "Dottie")
    assert "OPENBASE_SUPER_AGENT_THREAD_ID" not in calls[0][1].get("env", {})


def test_announce_super_agent_start_omits_announcement_without_agent_name(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("OPENBASE_CODER_CLI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(livekit_start_announcer, "_has_livekit_voice_route", lambda: True)

    announced = asyncio.run(
        livekit_start_announcer.announce_super_agent_start(
            thread_id="thread-1",
            turn_id="turn-1",
            agent_name=None,
            issue="Inspect repo",
        )
    )

    assert announced is False
