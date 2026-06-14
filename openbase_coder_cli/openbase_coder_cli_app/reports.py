"""Project report artifact API views."""

from __future__ import annotations

import base64
import mimetypes
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from asgiref.sync import async_to_sync
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from super_agents.app_server_client import DEFAULT_STATE_FILE
from super_agents.state import SessionRecord, read_state_file_locked

from openbase_coder_cli.mcp.projects import get_recent_projects as _get_recent_projects
from openbase_coder_cli.mcp.session_manager import get_session_manager
from openbase_coder_cli.openbase_coder_cli_app.item_tags import (
    report_tags,
    report_tags_payload,
    set_report_tags,
)
from openbase_coder_cli.paths import CODEX_HOME_DIR, NORMAL_CODEX_HOME_DIR

REPORTS_DIRECTORY = ".reports"
REPORTS_TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
REPORTS_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
REPORTS_MAX_FILES = 200
REPORTS_MAX_TEXT_BYTES = 1024 * 1024
REPORTS_MAX_IMAGE_BYTES = 5 * 1024 * 1024
HOME_REPORTS_PROJECT_DIR = Path.home()
REPORT_ACTION_PROMPT_MAX_CHARS = 24000
REPORT_ORIGIN_TIME_WINDOW_SECONDS = 10 * 60
SUPER_AGENTS_STATE_FILE_ENV = "SUPER_AGENTS_STATE_FILE"
REPORT_THREAD_ID_RE = re.compile(
    r"(?im)^\s*(?:super agent\s+)?thread\s+id\s*:\s*([A-Za-z0-9._:-]+)\s*$"
)
REPORT_THREAD_NAME_RE = re.compile(r"(?im)^\s*super agent thread name\s*:\s*(.+?)\s*$")
ACTION_HEADING_RE = re.compile(
    r"(?i)^#{1,6}\s*(action items?|next steps?|follow[- ]?ups?|todo|to do|implementation|recommendations?)\b"
)
MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+")
CHECKBOX_ACTION_RE = re.compile(r"(?im)^\s*(?:[-*]|\d+[.)])\s+\[\s\]\s+\S.*$")
ACTION_LINE_RE = re.compile(
    r"(?im)^\s*(?:[-*]|\d+[.)])\s+(?:\[[ xX]\]\s*)?"
    r"(?:action item|todo|to do|implement|fix|start|add|update|remove|investigate|follow up|follow-up)\b.*$"
)


@dataclass(frozen=True)
class ReportActionOrigin:
    thread_id: str
    label: str | None = None
    agent_name: str | None = None
    source: str = "unknown"


def _reports_dir(project_path: str) -> Path:
    return Path(project_path).expanduser().resolve() / REPORTS_DIRECTORY


def _reports_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in REPORTS_TEXT_EXTENSIONS:
        return "markdown" if suffix in {".md", ".markdown"} else "text"
    if suffix in REPORTS_IMAGE_EXTENSIONS:
        return "image"
    return "other"


def _reports_file_payload(path: Path, reports_dir: Path) -> dict:
    stat = path.stat()
    relative_path = str(path.relative_to(reports_dir))
    project_path = str(reports_dir.parent)
    return {
        "path": relative_path,
        "name": path.name,
        "kind": _reports_kind(path),
        "size": stat.st_size,
        "updated_at": stat.st_mtime,
        "tags": report_tags(project_path, relative_path),
    }


def _list_reports_files(project_path: str) -> list[dict]:
    reports_dir = _reports_dir(project_path).resolve()
    if not reports_dir.is_dir():
        return []

    files: list[dict] = []
    for candidate in sorted(reports_dir.rglob("*")):
        if len(files) >= REPORTS_MAX_FILES:
            break
        if not candidate.is_file():
            continue
        try:
            resolved = candidate.resolve()
            resolved.relative_to(reports_dir)
        except (OSError, ValueError):
            continue
        try:
            files.append(_reports_file_payload(resolved, reports_dir))
        except OSError:
            continue

    return sorted(files, key=lambda item: item["updated_at"], reverse=True)


def _reports_summary(project_path: str) -> dict:
    files = _list_reports_files(project_path)
    updated_at = files[0]["updated_at"] if files else None
    return {
        "reports_count": len(files),
        "reports_updated_at": updated_at,
    }


def _global_reports_projects() -> list[dict]:
    projects: list[dict] = []
    seen: set[Path] = set()
    for project_dir in (
        CODEX_HOME_DIR,
        NORMAL_CODEX_HOME_DIR,
        HOME_REPORTS_PROJECT_DIR,
    ):
        try:
            resolved = project_dir.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not _reports_dir(str(resolved)).is_dir():
            continue
        seen.add(resolved)
        project = {
            "path": str(resolved),
            "global_reports": True,
        }
        project.update(_reports_summary(str(resolved)))
        projects.append(project)
    return projects


def _all_reports_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[Path] = set()

    projects = _global_reports_projects() + _get_recent_projects()
    for project in projects:
        project_path = str(project.get("path", "")).strip()
        if not project_path:
            continue
        try:
            resolved = Path(project_path).expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)

        project_payload = dict(project)
        project_payload["path"] = str(resolved)
        for file_payload in _list_reports_files(str(resolved)):
            items.append(
                {
                    "id": f"{resolved}:{file_payload['path']}",
                    "project": project_payload,
                    "file": file_payload,
                    "updated_at": file_payload["updated_at"],
                }
            )

    return sorted(items, key=lambda item: item["updated_at"], reverse=True)


def _resolve_reports_path(project_path: str, relative_path: str) -> tuple[Path, Path]:
    if not relative_path:
        raise ValueError("file is required")

    reports_dir = _reports_dir(project_path).resolve()
    candidate = (reports_dir / relative_path).resolve()
    try:
        candidate.relative_to(reports_dir)
    except ValueError as exc:
        raise ValueError("file must be inside .reports") from exc
    return candidate, reports_dir


def _resolve_reports_file(project_path: str, relative_path: str) -> Path:
    candidate, _reports_dir_path = _resolve_reports_path(project_path, relative_path)
    if not candidate.is_file():
        raise FileNotFoundError(relative_path)
    return candidate


def _super_agents_state_path() -> Path:
    configured = os.environ.get(SUPER_AGENTS_STATE_FILE_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_STATE_FILE


def _extract_report_action_items(content: str) -> list[str]:
    action_items: list[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        normalized = line.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            action_items.append(normalized)

    lines = content.splitlines()
    in_action_section = False
    for line in lines:
        if MARKDOWN_HEADING_RE.match(line):
            in_action_section = bool(ACTION_HEADING_RE.match(line))
            if in_action_section:
                add(line)
            continue
        if in_action_section:
            if line.strip():
                add(line)

    for pattern in (CHECKBOX_ACTION_RE, ACTION_LINE_RE):
        for match in pattern.finditer(content):
            add(match.group(0))

    return action_items[:80]


def _parse_report_thread_id(content: str) -> str | None:
    match = REPORT_THREAD_ID_RE.search(content)
    if not match:
        return None
    return match.group(1).strip() or None


def _parse_report_thread_name(content: str) -> str | None:
    match = REPORT_THREAD_NAME_RE.search(content)
    if not match:
        return None
    return match.group(1).strip() or None


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _session_sort_time(session: SessionRecord) -> datetime:
    return (
        _parse_iso_timestamp(session.last_finished_at)
        or _parse_iso_timestamp(session.last_started_at)
        or _parse_iso_timestamp(session.updated_at)
        or datetime.fromtimestamp(0, tz=UTC)
    )


def _session_report_delta_seconds(
    session: SessionRecord,
    report_updated_at: float,
) -> float:
    report_time = datetime.fromtimestamp(report_updated_at, tz=UTC)
    values = [
        session.last_finished_at,
        session.last_started_at,
        session.last_event_at,
        session.updated_at,
    ]
    if session.turns:
        for turn in session.turns.values():
            values.extend([turn.finished_at, turn.updated_at, turn.started_at])

    deltas = [
        abs((report_time - parsed).total_seconds())
        for parsed in (_parse_iso_timestamp(value) for value in values)
        if parsed is not None
    ]
    return min(deltas) if deltas else float("inf")


def _session_matches_cwd(session: SessionRecord, project_path: Path) -> bool:
    if not session.cwd:
        return False
    try:
        return Path(session.cwd).expanduser().resolve() == project_path
    except OSError:
        return False


def _origin_from_session(session: SessionRecord, source: str) -> ReportActionOrigin:
    return ReportActionOrigin(
        thread_id=session.thread_id,
        label=session.label,
        agent_name=session.agent_name,
        source=source,
    )


def _resolve_report_origin(
    content: str,
    project_path: Path,
    report_updated_at: float,
) -> tuple[ReportActionOrigin | None, str | None]:
    state = read_state_file_locked(_super_agents_state_path())
    explicit_thread_id = _parse_report_thread_id(content)
    if explicit_thread_id:
        session = state.sessions.get(explicit_thread_id)
        if session is not None:
            return _origin_from_session(session, "report_thread_id"), None
        return ReportActionOrigin(
            thread_id=explicit_thread_id,
            source="report_thread_id",
        ), None

    explicit_name = _parse_report_thread_name(content)
    if explicit_name:
        label_matches = [
            session
            for session in state.sessions.values()
            if session.label == explicit_name
        ]
        cwd_matches = [
            session
            for session in label_matches
            if _session_matches_cwd(session, project_path)
        ]
        matches = cwd_matches or label_matches
        if matches:
            selected = sorted(matches, key=_session_sort_time, reverse=True)[0]
            return _origin_from_session(selected, "report_thread_name"), None
        return None, f"No Super Agent thread named {explicit_name!r} was found."

    cwd_matches = [
        session
        for session in state.sessions.values()
        if _session_matches_cwd(session, project_path)
    ]
    if len(cwd_matches) == 1:
        return _origin_from_session(cwd_matches[0], "project_thread"), None
    if len(cwd_matches) > 1:
        scored = sorted(
            (
                (_session_report_delta_seconds(session, report_updated_at), session)
                for session in cwd_matches
            ),
            key=lambda item: item[0],
        )
        close_matches = [
            item for item in scored if item[0] <= REPORT_ORIGIN_TIME_WINDOW_SECONDS
        ]
        if len(close_matches) == 1:
            return _origin_from_session(
                close_matches[0][1],
                "project_thread_report_time",
            ), None
        return (
            None,
            "Multiple Super Agent threads match this project, and the report does not identify which one created it.",
        )

    return (
        None,
        "The originating Super Agent thread could not be determined from this report.",
    )


def _report_action_prompt(
    *,
    project_path: Path,
    relative_path: str,
    content: str,
    action_items: list[str],
) -> str:
    excerpt = content
    truncated = False
    if len(excerpt) > REPORT_ACTION_PROMPT_MAX_CHARS:
        excerpt = excerpt[:REPORT_ACTION_PROMPT_MAX_CHARS].rstrip()
        truncated = True

    action_text = "\n".join(action_items)
    truncation_note = (
        "\n\nThe report content below was truncated for prompt size."
        if truncated
        else ""
    )
    return (
        "Implement the action items from this report in the same project.\n\n"
        f"Project path: {project_path}\n"
        f"Report file: .reports/{relative_path}\n\n"
        "Focus on the report's actionable implementation work. Inspect the code first, "
        "keep the change scoped to the report, preserve existing behavior outside the "
        "requested work, and run focused verification when practical.\n\n"
        "Detected action items:\n"
        f"{action_text}\n\n"
        f"Report content:{truncation_note}\n\n"
        f"{excerpt}"
    )


@api_view(["GET"])
def project_reports(request):
    """List developer communication files for a project."""
    project_path = request.query_params.get("path", "").strip()
    if not project_path:
        return Response(
            {"error": "path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resolved = Path(project_path).expanduser().resolve()
    if not resolved.is_dir():
        return Response(
            {"error": f"Directory not found: {resolved}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    files = _list_reports_files(str(resolved))
    return Response(
        {
            "directory": str(_reports_dir(str(resolved))),
            "files": files,
        }
    )


@api_view(["GET"])
def global_reports_projects(request):
    """List global report source directories outside recent projects."""
    return Response({"projects": _global_reports_projects()})


@api_view(["GET"])
def all_project_reports(request):
    """List all report artifacts across recent and global report sources."""
    return Response({"items": _all_reports_items()})


@api_view(["POST"])
def project_reports_action(request):
    """Start an implementation turn for actionable report items."""
    project_path = str(request.data.get("path", "")).strip()
    relative_path = str(request.data.get("file", "")).strip()
    if not project_path:
        return Response(
            {"error": "path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resolved = Path(project_path).expanduser().resolve()
    if not resolved.is_dir():
        return Response(
            {"error": f"Directory not found: {resolved}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        file_path = _resolve_reports_file(str(resolved), relative_path)
    except FileNotFoundError:
        return Response(
            {"error": f"File not found: {relative_path}"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    kind = _reports_kind(file_path)
    if kind not in {"markdown", "text"}:
        return Response(
            {
                "error": "Only Markdown or text reports can start implementation turns.",
                "reason": "unsupported_report_kind",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    size = file_path.stat().st_size
    if size > REPORTS_MAX_TEXT_BYTES:
        return Response(
            {
                "error": "Report is too large to inspect for action items.",
                "reason": "report_too_large",
            },
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    content = file_path.read_text(encoding="utf-8", errors="replace")
    action_items = _extract_report_action_items(content)
    if not action_items:
        return Response(
            {
                "error": "No action items were found in this report.",
                "reason": "no_action_items",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    origin, origin_error = _resolve_report_origin(
        content, resolved, file_path.stat().st_mtime
    )
    if origin is None:
        return Response(
            {
                "error": origin_error
                or "The originating Super Agent thread could not be determined.",
                "reason": "origin_unknown",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    prompt = _report_action_prompt(
        project_path=resolved,
        relative_path=relative_path,
        content=content,
        action_items=action_items,
    )
    try:
        turn_id = async_to_sync(get_session_manager().start_turn)(
            origin.thread_id, prompt
        )
    except ValueError as exc:
        return Response(
            {"error": str(exc), "reason": "turn_start_failed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "status": "started",
            "thread_id": origin.thread_id,
            "turn_id": turn_id,
            "thread_name": origin.label,
            "agent_name": origin.agent_name,
            "origin_source": origin.source,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "DELETE", "PATCH"])
def project_reports_file(request):
    """Return, update, or delete a renderable developer communication file."""
    project_path = request.query_params.get("path", "").strip()
    relative_path = request.query_params.get("file", "").strip()
    if not project_path:
        return Response(
            {"error": "path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resolved = Path(project_path).expanduser().resolve()
    if not resolved.is_dir():
        return Response(
            {"error": f"Directory not found: {resolved}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "DELETE":
        try:
            file_path, reports_dir = _resolve_reports_path(str(resolved), relative_path)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not file_path.exists():
            return Response(
                {"error": f"File not found: {relative_path}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not file_path.is_file():
            return Response(
                {"error": "Report path must be a file"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_payload = _reports_file_payload(file_path, reports_dir)
            file_path.unlink()
        except OSError as exc:
            return Response(
                {"error": f"Unable to delete report: {exc.strerror or exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"deleted": True, "file": file_payload})

    if request.method == "PATCH":
        try:
            file_path, reports_dir = _resolve_reports_path(str(resolved), relative_path)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not file_path.exists():
            return Response(
                {"error": f"File not found: {relative_path}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not file_path.is_file():
            return Response(
                {"error": "Report path must be a file"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        kind = _reports_kind(file_path)
        if kind not in {"markdown", "text"}:
            return Response(
                {"error": "Only markdown and text reports can be edited."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        content = request.data.get("content")
        if not isinstance(content, str):
            return Response(
                {"error": "content must be a string"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(content.encode("utf-8")) > REPORTS_MAX_TEXT_BYTES:
            return Response(
                {"error": "File is too large to save as text"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        try:
            file_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return Response(
                {"error": f"Unable to save report: {exc.strerror or exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "file": _reports_file_payload(file_path, reports_dir),
                "content": content,
            }
        )

    try:
        file_path = _resolve_reports_file(str(resolved), relative_path)
    except FileNotFoundError:
        return Response(
            {"error": f"File not found: {relative_path}"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    kind = _reports_kind(file_path)
    size = file_path.stat().st_size
    if kind in {"markdown", "text"}:
        if size > REPORTS_MAX_TEXT_BYTES:
            return Response(
                {"error": "File is too large to render as text"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        return Response(
            {
                "file": _reports_file_payload(file_path, _reports_dir(str(resolved))),
                "content": file_path.read_text(encoding="utf-8", errors="replace"),
            }
        )

    if kind == "image":
        if size > REPORTS_MAX_IMAGE_BYTES:
            return Response(
                {"error": "Image is too large to render inline"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        media_type = (
            mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        )
        data = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return Response(
            {
                "file": _reports_file_payload(file_path, _reports_dir(str(resolved))),
                "data_url": f"data:{media_type};base64,{data}",
            }
        )

    return Response(
        {
            "file": _reports_file_payload(file_path, _reports_dir(str(resolved))),
            "error": "This file type is not renderable in the console yet.",
        },
        status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    )


@api_view(["GET", "PATCH"])
def project_reports_tags(request):
    """Read or update local tag metadata for one report artifact."""
    project_path = request.query_params.get("path", "").strip()
    relative_path = request.query_params.get("file", "").strip()
    if not project_path:
        return Response(
            {"error": "path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resolved = Path(project_path).expanduser().resolve()
    if not resolved.is_dir():
        return Response(
            {"error": f"Directory not found: {resolved}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        _resolve_reports_file(str(resolved), relative_path)
    except FileNotFoundError:
        return Response(
            {"error": f"File not found: {relative_path}"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "GET":
        return Response(report_tags_payload(str(resolved), relative_path))

    tags = request.data.get("tags")
    if not isinstance(tags, list):
        return Response(
            {"error": "tags must be a list"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        payload = set_report_tags(str(resolved), relative_path, tags)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(payload)


@api_view(["GET"])
def project_reports_download(request):
    """Download any report artifact as a raw file."""
    project_path = request.query_params.get("path", "").strip()
    relative_path = request.query_params.get("file", "").strip()
    if not project_path:
        return Response(
            {"error": "path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resolved = Path(project_path).expanduser().resolve()
    if not resolved.is_dir():
        return Response(
            {"error": f"Directory not found: {resolved}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        file_path = _resolve_reports_file(str(resolved), relative_path)
    except FileNotFoundError:
        return Response(
            {"error": f"File not found: {relative_path}"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(
        file_path.open("rb"),
        as_attachment=True,
        filename=file_path.name,
        content_type=media_type,
    )
