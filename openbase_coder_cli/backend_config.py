from __future__ import annotations

CODEX_BACKEND = "codex"
OPENBASE_CLOUD_BACKEND = "openbase_cloud"
CLAUDE_CODE_BACKEND = "claude_code"
SUPPORTED_BACKENDS = (CODEX_BACKEND, OPENBASE_CLOUD_BACKEND, CLAUDE_CODE_BACKEND)
DEFAULT_CODING_BACKEND = "codex"
CODING_BACKEND_ENV_KEY = "OPENBASE_CODING_BACKEND"
LEGACY_CODEX_BACKEND_ENV_KEY = "OPENBASE_CODEX_BACKEND"
BACKEND_ALIASES = {
    "codex": CODEX_BACKEND,
    "openai": CODEX_BACKEND,
    "openbase": OPENBASE_CLOUD_BACKEND,
    "openbase-cloud": OPENBASE_CLOUD_BACKEND,
    "openbase_cloud": OPENBASE_CLOUD_BACKEND,
    "cloud": OPENBASE_CLOUD_BACKEND,
    "claude": CLAUDE_CODE_BACKEND,
    "claude-code": CLAUDE_CODE_BACKEND,
    "claude_code": CLAUDE_CODE_BACKEND,
    "claude-agent": CLAUDE_CODE_BACKEND,
    "claude-agent-sdk": CLAUDE_CODE_BACKEND,
    "claude_agent_sdk": CLAUDE_CODE_BACKEND,
    "claude-sdk": CLAUDE_CODE_BACKEND,
    "claude-tui": CLAUDE_CODE_BACKEND,
    "claude-code-tui": CLAUDE_CODE_BACKEND,
}


def normalize_backend(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return DEFAULT_CODING_BACKEND
    try:
        return BACKEND_ALIASES[raw]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_BACKENDS)
        raise ValueError(
            f"Unsupported backend: {value}. Supported backends: {supported}."
        ) from exc
