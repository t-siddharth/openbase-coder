from __future__ import annotations

import os
from pathlib import Path


def brain_score_token_file() -> Path:
    return Path(
        os.getenv(
            "OPENBASE_BRAIN_SCORE_TOKEN_FILE",
            str(Path.home() / ".openbase" / "brain_score_token"),
        )
    ).expanduser()


def load_brain_score_token() -> str:
    configured = os.getenv("OPENBASE_BRAIN_SCORE_TOKEN", "").strip()
    if configured:
        return configured
    try:
        return brain_score_token_file().read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def save_brain_score_token(token: str) -> Path:
    stripped = token.strip()
    if not stripped:
        raise ValueError("Brain score token cannot be empty.")

    path = brain_score_token_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"{stripped}\n")
    finally:
        os.chmod(path, 0o600)
    return path


def brain_score_token_configured() -> bool:
    return bool(load_brain_score_token())
