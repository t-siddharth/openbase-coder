"""
Serve the built React console as static files with SPA catch-all.
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse


def serve_console(request: HttpRequest, path: str = "") -> HttpResponse:
    """Serve built console files, falling back to index.html for SPA routing."""
    build_dir = settings.CONSOLE_BUILD_DIR

    if not build_dir or not build_dir.is_dir():
        return HttpResponse(
            "Console not built. Run `openbase-coder setup` "
            "or `npm run build` in the console directory.",
            status=502,
            content_type="text/plain",
        )

    build_root = build_dir.resolve()

    # Try to serve the exact file
    rel_path = Path(path.lstrip("/"))
    file_path = (build_root / rel_path).resolve()
    if path and file_path.is_file() and file_path.is_relative_to(build_root):
        content_type, _ = mimetypes.guess_type(str(file_path))
        return FileResponse(
            open(file_path, "rb"),
            content_type=content_type or "application/octet-stream",
        )

    # SPA fallback: serve index.html
    index_path = build_dir / "index.html"
    if index_path.is_file():
        return FileResponse(
            open(index_path, "rb"),
            content_type="text/html",
        )

    return HttpResponse(
        "Console not built. Run `openbase-coder setup` "
        "or `npm run build` in the console directory.",
        status=502,
        content_type="text/plain",
    )
