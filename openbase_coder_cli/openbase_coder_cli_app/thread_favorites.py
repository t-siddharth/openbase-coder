"""Local favorite metadata for Codex threads."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openbase_coder_cli.cli.utils import get_data_dir

FAVORITES_FILE = "thread-favorites.json"

_lock = threading.Lock()


def favorite_payload(thread_id: str | None) -> dict[str, str | bool | None]:
    """Return API metadata for one thread's favorite state."""
    normalized = _normalize_thread_id(thread_id)
    entry = _read_favorites().get(normalized) if normalized else None
    favorited_at = entry.get("favorited_at") if isinstance(entry, dict) else None
    return {
        "thread_id": normalized,
        "is_favorite": bool(entry),
        "favorited_at": favorited_at if isinstance(favorited_at, str) else None,
    }


def is_thread_favorite(thread_id: str | None) -> bool:
    return bool(favorite_payload(thread_id)["is_favorite"])


def set_thread_favorite(thread_id: str, is_favorite: bool) -> dict[str, str | bool | None]:
    """Set or clear favorite metadata for a thread."""
    normalized = _normalize_thread_id(thread_id)
    if not normalized:
        raise ValueError("thread_id is required")

    with _lock:
        favorites = _read_favorites_unlocked()
        if is_favorite:
            current = favorites.get(normalized) if isinstance(favorites.get(normalized), dict) else {}
            favorites[normalized] = {
                "thread_id": normalized,
                "favorited_at": current.get("favorited_at") or _utc_now(),
            }
        else:
            favorites.pop(normalized, None)
        _write_favorites_unlocked(favorites)
    return favorite_payload(normalized)


def favorite_thread_ids() -> set[str]:
    return set(_read_favorites())


def _favorites_path() -> Path:
    return get_data_dir() / FAVORITES_FILE


def _read_favorites() -> dict[str, dict[str, Any]]:
    with _lock:
        return _read_favorites_unlocked()


def _read_favorites_unlocked() -> dict[str, dict[str, Any]]:
    path = _favorites_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    threads = payload.get("threads") if isinstance(payload, dict) else None
    if not isinstance(threads, dict):
        return {}
    favorites: dict[str, dict[str, Any]] = {}
    for raw_thread_id, raw_entry in threads.items():
        thread_id = _normalize_thread_id(raw_thread_id)
        if not thread_id or not isinstance(raw_entry, dict):
            continue
        favorites[thread_id] = _entry_payload(thread_id, raw_entry)
    return favorites


def _write_favorites_unlocked(favorites: dict[str, dict[str, Any]]) -> None:
    path = _favorites_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"threads": favorites}
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def _entry_payload(thread_id: str, raw_entry: dict[str, Any]) -> dict[str, str | None]:
    favorited_at = raw_entry.get("favorited_at")
    return {
        "thread_id": thread_id,
        "favorited_at": favorited_at if isinstance(favorited_at, str) else None,
    }


def _normalize_thread_id(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
