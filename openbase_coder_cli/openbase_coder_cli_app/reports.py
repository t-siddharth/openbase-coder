"""Project report artifact API views."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from openbase_coder_cli.paths import CODEX_HOME_DIR, NORMAL_CODEX_HOME_DIR

REPORTS_DIRECTORY = ".reports"
REPORTS_TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
REPORTS_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
REPORTS_MAX_FILES = 200
REPORTS_MAX_TEXT_BYTES = 1024 * 1024
REPORTS_MAX_IMAGE_BYTES = 5 * 1024 * 1024
HOME_REPORTS_PROJECT_DIR = Path.home()

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
    return {
        "path": str(path.relative_to(reports_dir)),
        "name": path.name,
        "kind": _reports_kind(path),
        "size": stat.st_size,
        "updated_at": stat.st_mtime,
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


@api_view(["GET", "DELETE"])
def project_reports_file(request):
    """Return or delete a renderable developer communication file."""
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
