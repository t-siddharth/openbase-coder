from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openbase_coder_cli.services.installation import InstallationConfig

BOILERSYNC_TIMEOUT_SECONDS = 30


def boilersync_templates_payload(template_ref: str | None = None) -> dict[str, Any]:
    boilersync_bin = resolve_boilersync_binary()
    if not boilersync_bin:
        return {
            "boilersync_available": False,
            "boilersync_path": None,
            "sources": None,
            "templates": None,
            "details": None,
            "error": "boilersync was not found on PATH.",
        }

    sources_result = run_boilersync_json(
        boilersync_bin, "templates", "sources", "--json"
    )
    templates_result = run_boilersync_json(
        boilersync_bin, "templates", "list", "--json"
    )
    details_result = None
    if template_ref:
        details_result = run_boilersync_json(
            boilersync_bin,
            "templates",
            "details",
            template_ref,
            "--json",
        )

    errors = [
        result["error"]
        for result in (sources_result, templates_result, details_result)
        if result and result["error"]
    ]

    return {
        "boilersync_available": True,
        "boilersync_path": boilersync_bin,
        "sources": sources_result["payload"],
        "templates": templates_result["payload"],
        "details": details_result["payload"] if details_result else None,
        "error": "\n".join(errors) if errors else None,
    }


def run_boilersync_json(boilersync_bin: str, *args: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [boilersync_bin, *args],
            capture_output=True,
            text=True,
            timeout=BOILERSYNC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return {"payload": None, "error": f"boilersync timed out: {exc}"}
    except OSError as exc:
        return {"payload": None, "error": f"Unable to run boilersync: {exc}"}

    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"boilersync {' '.join(args)} failed."
        )
        return {"payload": None, "error": detail}

    try:
        return {"payload": json.loads(result.stdout), "error": None}
    except json.JSONDecodeError as exc:
        return {
            "payload": None,
            "error": f"Unable to parse boilersync JSON output: {exc}",
        }


def resolve_boilersync_binary() -> str | None:
    for candidate in preferred_boilersync_binary_candidates():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("boilersync")


def preferred_boilersync_binary_candidates() -> list[Path]:
    candidates: list[Path] = []

    if InstallationConfig.exists():
        try:
            workspace = Path(InstallationConfig.load().workspace_path)
        except (OSError, ValueError, TypeError):
            workspace = None
        if workspace is not None:
            candidates.extend(
                [
                    workspace / ".venv" / "bin" / "boilersync",
                    workspace / "cli" / ".venv" / "bin" / "boilersync",
                ]
            )

    candidates.extend(
        [
            Path.home() / ".local" / "bin" / "boilersync",
            Path("/opt/homebrew/bin/boilersync"),
            Path("/usr/local/bin/boilersync"),
        ]
    )

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        deduped.append(candidate)
        seen.add(candidate)
    return deduped
