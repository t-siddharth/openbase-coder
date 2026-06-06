from __future__ import annotations

import json
from pathlib import Path


def multi_repo_names(directory: str | Path) -> list[str]:
    """Return sub-repo directory names declared by a workspace multi.json."""
    multi_path = Path(directory) / "multi.json"
    if not multi_path.is_file():
        return []
    try:
        data = json.loads(multi_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    names: list[str] = []
    for repo in data.get("repos", []):
        if not isinstance(repo, dict):
            continue
        name = repo.get("name") or str(repo.get("url", "")).rstrip("/").split("/")[-1]
        if isinstance(name, str) and name:
            names.append(name)
    return names


def multi_repo_name_set(directory: str | Path) -> set[str]:
    return set(multi_repo_names(directory))
