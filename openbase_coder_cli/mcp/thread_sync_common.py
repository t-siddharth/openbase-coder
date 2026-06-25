"""Shared helpers for thread sync implementations."""

from __future__ import annotations

import json
import logging
import os
import platform
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    device_name: str
    created_at: float

    def to_json(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "created_at": self.created_at,
        }


def get_or_create_device_identity(path: Path) -> DeviceIdentity:
    existing = read_device_identity(path)
    if existing is not None:
        return existing
    identity = DeviceIdentity(
        device_id=str(uuid.uuid4()),
        device_name=platform.node() or "unknown-device",
        created_at=time.time(),
    )
    write_json_atomic(path, identity.to_json())
    return identity


def read_device_identity(path: Path) -> DeviceIdentity | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    device_id = raw.get("device_id")
    device_name = raw.get("device_name")
    created_at = raw.get("created_at")
    if not isinstance(device_id, str) or not isinstance(device_name, str):
        return None
    if not isinstance(created_at, int | float):
        created_at = 0.0
    return DeviceIdentity(device_id, device_name, float(created_at))


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp:
        tmp.write(body)
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def read_scoped_ledger(
    path: Path,
    *,
    scope_key: str,
    logger: logging.Logger,
    malformed_event: str,
) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("%s path=%s", malformed_event, path)
        return {}
    if not isinstance(raw, dict):
        return {}
    entries = raw.get(scope_key)
    return entries if isinstance(entries, dict) else {}


def write_scoped_ledger(path: Path, *, scope_key: str, ledger: dict[str, Any]) -> None:
    write_json_atomic(path, {scope_key: ledger})


def read_device_ledger(
    path: Path,
    *,
    scope_key: str,
    logger: logging.Logger,
    malformed_event: str,
) -> dict[str, Any]:
    if not path.exists():
        return {scope_key: {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("%s path=%s", malformed_event, path)
        return {scope_key: {}}
    if not isinstance(raw, dict):
        return {scope_key: {}}
    if not isinstance(raw.get(scope_key), dict):
        raw[scope_key] = {}
    return raw


def device_ledger_entry(
    ledger: dict[str, Any],
    *,
    scope_key: str,
    entity_id: str,
) -> dict[str, Any]:
    entries = ledger.setdefault(scope_key, {})
    entry = entries.setdefault(entity_id, {})
    entry.setdefault("devices", {})
    return entry


def device_exported_fingerprints(
    entry_ledger: dict[str, Any], device_id: str
) -> set[str]:
    device = entry_ledger.get("devices", {}).get(device_id)
    snapshots = device.get("snapshots") if isinstance(device, dict) else None
    if not isinstance(snapshots, dict):
        return set()
    return {
        fingerprint
        for fingerprint, value in snapshots.items()
        if isinstance(fingerprint, str)
        and isinstance(value, dict)
        and value.get("status") == "exported"
    }


def snapshot_already_imported(
    entry_ledger: dict[str, Any],
    *,
    device_id: str,
    fingerprint_id: str,
) -> bool:
    device = entry_ledger.get("devices", {}).get(device_id)
    snapshots = device.get("snapshots") if isinstance(device, dict) else None
    snapshot = snapshots.get(fingerprint_id) if isinstance(snapshots, dict) else None
    return isinstance(snapshot, dict) and snapshot.get("status") in {
        "ignored",
        "imported",
        "same_content",
    }


def record_device_snapshot(
    entry_ledger: dict[str, Any],
    *,
    device_id: str,
    fingerprint_id: str,
    snapshot_path: Path,
    status: str,
) -> None:
    devices = entry_ledger.setdefault("devices", {})
    device = devices.setdefault(device_id, {})
    snapshots = device.setdefault("snapshots", {})
    snapshots[fingerprint_id] = {
        "fingerprint": fingerprint_id,
        "snapshot_path": str(snapshot_path),
        "status": status,
        "seen_at": time.time(),
    }


def record_device_conflict(
    entry_ledger: dict[str, Any],
    *,
    local_fingerprint: str | None,
    incoming_fingerprint: str,
    source_device_id: str,
    reason: str,
    snapshot_path: Path | None = None,
) -> None:
    conflict = {
        "reason": reason,
        "local_fingerprint": local_fingerprint,
        "incoming_fingerprint": incoming_fingerprint,
        "source_device_id": source_device_id,
        "detected_at": time.time(),
    }
    if snapshot_path is not None:
        conflict["snapshot_path"] = str(snapshot_path)
    entry_ledger["conflict"] = conflict


def import_snapshot_decision(
    *,
    has_local: bool,
    local_fingerprint: str | None,
    incoming_fingerprint: str,
    parent_fingerprint: str | None,
    entry_ledger: dict[str, Any],
) -> str:
    if local_fingerprint == incoming_fingerprint:
        return "same_content"
    if not has_local:
        return "import"
    if parent_fingerprint and local_fingerprint == parent_fingerprint:
        return "import"
    if (
        entry_ledger.get("local_fingerprint") == parent_fingerprint
        and parent_fingerprint
    ):
        return "import"
    return "conflict"


def parent_fingerprint_for_export(
    entry_ledger: dict[str, Any],
    fingerprint_id: str,
) -> str | None:
    parent = entry_ledger.get("local_fingerprint")
    if not isinstance(parent, str):
        return None
    return parent if parent and parent != fingerprint_id else None


def record_synced_pair(
    ledger: dict[str, Any],
    *,
    entity_key: str,
    entity_id: str,
    left_key: str,
    left_fingerprint: dict[str, Any],
    right_key: str,
    right_fingerprint: dict[str, Any],
    reason: str,
) -> None:
    ledger[entity_id] = {
        entity_key: entity_id,
        left_key: left_fingerprint,
        right_key: right_fingerprint,
        "status": "synced",
        "reason": reason,
        "synced_at": time.time(),
    }


def record_sync_conflict(
    ledger: dict[str, Any],
    *,
    entity_key: str,
    entity_id: str,
    left_key: str,
    left_fingerprint: dict[str, Any],
    right_key: str,
    right_fingerprint: dict[str, Any],
    reason: str,
) -> None:
    ledger[entity_id] = {
        entity_key: entity_id,
        left_key: left_fingerprint,
        right_key: right_fingerprint,
        "status": "conflict",
        "reason": reason,
        "synced_at": time.time(),
    }


def fingerprint_matches(
    value: Any,
    fingerprint: dict[str, Any],
    *,
    keys: tuple[str, ...],
) -> bool:
    return isinstance(value, dict) and all(
        value.get(key) == fingerprint.get(key) for key in keys
    )
