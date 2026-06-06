from __future__ import annotations

# ruff: noqa: E402, I001

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

os.environ.setdefault("OPENBASE_CODER_CLI_SECRET_KEY", "test-secret")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openbase_coder_cli.config.settings")

import django
from rest_framework.test import APIRequestFactory, force_authenticate

django.setup()

from openbase_coder_cli.mcp.models import ThreadInfo
from openbase_coder_cli.mcp.session_manager import ThreadListPage
from openbase_coder_cli.openbase_coder_cli_app import threads as thread_views


class FakeThreadManager:
    def __init__(self, threads: list[ThreadInfo]) -> None:
        self._threads = threads
        self.page_calls: list[dict[str, str | int | None]] = []

    async def list_threads(self) -> list[ThreadInfo]:
        return self._threads

    async def list_thread_page(
        self,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> ThreadListPage:
        self.page_calls.append({"limit": limit, "cursor": cursor})
        start = int(cursor or 0)
        next_index = start + limit
        next_cursor = str(next_index) if next_index < len(self._threads) else None
        return ThreadListPage(
            threads=self._threads[start:next_index],
            next_cursor=next_cursor,
        )

    async def get_thread_state(self, thread_id: str) -> ThreadInfo | None:
        raise RuntimeError(f"thread not loaded: {thread_id}")


def _thread(index: int) -> ThreadInfo:
    now = datetime(2026, 5, 28, 12, tzinfo=timezone.utc)
    updated_at = now - timedelta(minutes=index)
    return ThreadInfo(
        session_id=f"thread-{index:03d}",
        directory=f"/tmp/project-{index:03d}",
        created_at=updated_at,
        updated_at=updated_at,
    )


def _get_threads(monkeypatch, url: str, threads: list[ThreadInfo]):
    thread_views.invalidate_thread_list_cache()
    manager = FakeThreadManager(threads)
    monkeypatch.setattr(
        thread_views,
        "get_session_manager",
        lambda: manager,
    )
    monkeypatch.setattr(thread_views, "get_livekit_shared_thread_id", lambda: None)
    monkeypatch.setattr(thread_views, "_refresh_projects_from_threads", lambda _: None)

    factory = APIRequestFactory()
    request = factory.get(url)
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return thread_views.thread_list(request), manager


def test_thread_list_returns_default_first_page(monkeypatch) -> None:
    response, manager = _get_threads(
        monkeypatch,
        "/api/threads/",
        [_thread(index) for index in range(30)],
    )

    assert response.status_code == 200
    assert response.data["count"] == 26
    assert response.data["page"] == 1
    assert response.data["page_size"] == 25
    assert response.data["previous"] is None
    assert response.data["next"] == "/api/threads/?page=2&page_size=25&cursor=25"
    assert len(response.data["threads"]) == 25
    assert response.data["threads"][0]["thread_id"] == "thread-000"
    assert manager.page_calls == [{"limit": 25, "cursor": None}]


def test_thread_list_slices_requested_page(monkeypatch) -> None:
    response, manager = _get_threads(
        monkeypatch,
        "/api/threads/?page=2&page_size=10&cursor=10",
        [_thread(index) for index in range(25)],
    )

    assert response.status_code == 200
    assert response.data["count"] == 21
    assert response.data["page"] == 2
    assert response.data["page_size"] == 10
    assert response.data["previous"] == "/api/threads/?page=1&page_size=10"
    assert response.data["next"] == "/api/threads/?page=3&page_size=10&cursor=20"
    assert [thread["thread_id"] for thread in response.data["threads"]] == [
        f"thread-{index:03d}" for index in range(10, 20)
    ]
    assert manager.page_calls == [{"limit": 10, "cursor": "10"}]


def test_thread_list_rejects_invalid_pagination(monkeypatch) -> None:
    response, _ = _get_threads(
        monkeypatch,
        "/api/threads/?page=0&page_size=10",
        [_thread(index) for index in range(3)],
    )

    assert response.status_code == 400
    assert response.data["error"] == "page must be a positive integer"


def test_thread_list_caps_page_size(monkeypatch) -> None:
    response, _ = _get_threads(
        monkeypatch,
        "/api/threads/?page_size=500",
        [_thread(index) for index in range(125)],
    )

    assert response.status_code == 200
    assert response.data["page_size"] == 100
    assert len(response.data["threads"]) == 100
    assert response.data["next"] == "/api/threads/?page_size=100&page=2&cursor=100"


def test_thread_list_skips_unavailable_livekit_fallback(monkeypatch) -> None:
    thread_views.invalidate_thread_list_cache()
    monkeypatch.setattr(
        thread_views,
        "get_session_manager",
        lambda: FakeThreadManager([_thread(1)]),
    )
    monkeypatch.setattr(
        thread_views,
        "get_livekit_shared_thread_id",
        lambda: "missing-dispatcher-thread",
    )
    monkeypatch.setattr(thread_views, "_refresh_projects_from_threads", lambda _: None)

    factory = APIRequestFactory()
    request = factory.get("/api/threads/?page_size=25")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    response = thread_views.thread_list(request)

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert [thread["thread_id"] for thread in response.data["threads"]] == [
        "thread-001"
    ]
