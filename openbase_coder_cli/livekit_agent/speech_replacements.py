from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TTS_REPLACEMENTS_PATH = Path.home() / ".openbase" / "tts-replacements.json"
TTS_REPLACEMENTS_PATH_ENV = "OPENBASE_CODER_TTS_REPLACEMENTS_PATH"


DEFAULT_ACRONYMS = (
    "AWS",
    "API",
    "CLI",
    "JSON",
    "TTS",
    "STT",
    "HTTP",
    "HTTPS",
    "XML",
    "HTML",
    "CSS",
    "JS",
    "TS",
    "TSX",
    "JSX",
    "SQL",
    "UI",
    "UX",
    "URL",
    "URI",
    "ID",
    "VAD",
    "LLM",
)
ACRONYMS = DEFAULT_ACRONYMS

DEFAULT_TERM_PRONUNCIATIONS = {
    "SaaS": "sass",
    "SAAS": "sass",
    "SAS": "sass",
}
TERM_PRONUNCIATIONS = DEFAULT_TERM_PRONUNCIATIONS


@dataclass(frozen=True)
class TTSReplacements:
    acronyms: tuple[str, ...]
    term_pronunciations: dict[str, str]


_REPLACEMENTS_CACHE: TTSReplacements | None = None
_REPLACEMENTS_CACHE_KEY: tuple[str, int | None, int | None] | None = None


def current_tts_replacements() -> TTSReplacements:
    """Return built-in plus user-configured TTS replacements, reloading on file changes."""

    global _REPLACEMENTS_CACHE, _REPLACEMENTS_CACHE_KEY

    path = _tts_replacements_path()
    stat_key = _stat_key(path)
    cache_key = (str(path), *stat_key)
    if _REPLACEMENTS_CACHE is not None and _REPLACEMENTS_CACHE_KEY == cache_key:
        return _REPLACEMENTS_CACHE

    replacements = _load_tts_replacements(path)
    _REPLACEMENTS_CACHE = replacements
    _REPLACEMENTS_CACHE_KEY = cache_key
    return replacements


def _tts_replacements_path() -> Path:
    configured = os.getenv(TTS_REPLACEMENTS_PATH_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_TTS_REPLACEMENTS_PATH


def _stat_key(path: Path) -> tuple[int | None, int | None]:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return (None, None)
    return (stat.st_mtime_ns, stat.st_size)


def _load_tts_replacements(path: Path) -> TTSReplacements:
    acronyms = list(DEFAULT_ACRONYMS)
    term_pronunciations = dict(DEFAULT_TERM_PRONUNCIATIONS)

    try:
        if not path.is_file():
            return TTSReplacements(tuple(acronyms), term_pronunciations)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("top-level value must be an object")
        _merge_acronyms(acronyms, payload.get("acronyms"))
        _merge_term_pronunciations(
            term_pronunciations,
            payload.get("term_pronunciations"),
        )
        _merge_term_pronunciations(term_pronunciations, payload.get("replacements"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(
            "Unable to load TTS replacements from %s: %s",
            path,
            exc,
        )
        return TTSReplacements(tuple(acronyms), term_pronunciations)

    return TTSReplacements(tuple(acronyms), term_pronunciations)


def _merge_acronyms(acronyms: list[str], configured: Any) -> None:
    if configured is None:
        return
    if not isinstance(configured, list):
        raise ValueError("acronyms must be a list of strings")
    existing = {acronym.upper() for acronym in acronyms}
    for item in configured:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("acronyms must be a list of non-empty strings")
        acronym = item.strip().upper()
        if acronym not in existing:
            acronyms.append(acronym)
            existing.add(acronym)


def _merge_term_pronunciations(
    term_pronunciations: dict[str, str],
    configured: Any,
) -> None:
    if configured is None:
        return
    if not isinstance(configured, dict):
        raise ValueError("term pronunciations must be an object")
    for term, pronunciation in configured.items():
        if (
            not isinstance(term, str)
            or not term.strip()
            or not isinstance(pronunciation, str)
            or not pronunciation.strip()
        ):
            raise ValueError("term pronunciations must map non-empty strings")
        term_pronunciations[term.strip()] = pronunciation.strip()

EXTENSION_SPEECH = {
    "md": "M D",
    "py": "P Y",
    "js": "J S",
    "jsx": "J S X",
    "ts": "T S",
    "tsx": "T S X",
    "json": "JSON",
    "yaml": "YAML",
    "yml": "YAML",
    "toml": "TOML",
    "lock": "lock",
    "txt": "text",
    "swift": "swift",
    "kt": "K T",
    "rs": "R S",
    "go": "go",
    "sh": "shell",
}

NUMBER_WORDS = {
    1: "One",
    2: "Two",
    3: "Three",
    4: "Four",
    5: "Five",
    6: "Six",
    7: "Seven",
    8: "Eight",
    9: "Nine",
    10: "Ten",
}

CODE_BLOCK_OMISSION_SPEECH = "Omitted."
