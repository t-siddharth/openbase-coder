from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from openbase_coder_cli.services.installation import InstallationConfig

TOOL_LINE_RE = re.compile(
    r"^(?P<name>\S+)\s+v(?P<version>\S+)(?P<meta>(?:\s+\[[^\]]+\])*)\s+\((?P<environment_path>[^)]+)\)$"
)
EXECUTABLE_LINE_RE = re.compile(r"^-\s+(?P<name>.+?)\s+\((?P<path>.+)\)$")
META_RE = re.compile(r"\[([^\]]+)\]")
HELP_OUTPUT_MAX_CHARS = 60_000


@dataclass
class UvToolExecutable:
    name: str
    path: str

    def to_dict(self) -> dict:
        return {"name": self.name, "path": self.path}


@dataclass
class UvTool:
    name: str
    version: str
    environment_path: str
    required_specifier: str | None = None
    python_version: str | None = None
    executables: list[UvToolExecutable] = field(default_factory=list)
    is_editable: bool = False
    editable_project_location: str | None = None
    editable_packages: list[dict] = field(default_factory=list)
    inspection_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "environment_path": self.environment_path,
            "required_specifier": self.required_specifier,
            "python_version": self.python_version,
            "executables": [executable.to_dict() for executable in self.executables],
            "is_editable": self.is_editable,
            "editable_project_location": self.editable_project_location,
            "editable_packages": self.editable_packages,
            "inspection_error": self.inspection_error,
        }


def list_uv_tools_payload() -> dict:
    uv_bin = _resolve_uv_binary()
    if not uv_bin:
        return {
            "uv_available": False,
            "uv_path": None,
            "tools": [],
            "error": "uv was not found on PATH.",
        }

    try:
        result = subprocess.run(
            [
                uv_bin,
                "tool",
                "list",
                "--show-paths",
                "--show-version-specifiers",
                "--show-python",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "uv_available": True,
            "uv_path": uv_bin,
            "tools": [],
            "error": f"Unable to run uv tool list: {exc}",
        }

    if result.returncode != 0:
        detail = (
            result.stderr.strip() or result.stdout.strip() or "uv tool list failed."
        )
        return {
            "uv_available": True,
            "uv_path": uv_bin,
            "tools": [],
            "error": detail,
        }

    tools = _parse_uv_tool_list(result.stdout)
    for tool in tools:
        _populate_editable_metadata(uv_bin, tool)

    return {
        "uv_available": True,
        "uv_path": uv_bin,
        "tools": [tool.to_dict() for tool in tools],
        "error": None,
    }


def uninstall_uv_tool(tool_name: str) -> None:
    uv_bin = _resolve_uv_binary()
    if not uv_bin:
        raise RuntimeError("uv was not found on PATH.")

    try:
        result = subprocess.run(
            [uv_bin, "tool", "uninstall", tool_name],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"uv tool uninstall timed out: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Unable to run uv tool uninstall: {exc}") from exc

    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"uv tool uninstall failed for {tool_name}."
        )
        raise RuntimeError(detail)


def uv_tool_help_payload(tool_name: str, executable_name: str) -> tuple[dict, int]:
    tools_payload = list_uv_tools_payload()
    if tools_payload.get("error"):
        return {
            "tool_name": tool_name,
            "executable_name": executable_name,
            "command": [executable_name, "--help"],
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error": tools_payload["error"],
        }, 400

    tool = next(
        (
            item
            for item in tools_payload.get("tools", [])
            if item.get("name") == tool_name
        ),
        None,
    )
    if tool is None:
        return {"error": f"uv tool not found: {tool_name}"}, 404

    executable = next(
        (
            item
            for item in tool.get("executables", [])
            if item.get("name") == executable_name
        ),
        None,
    )
    if executable is None:
        return {
            "error": f"executable not found for uv tool {tool_name}: {executable_name}"
        }, 404

    executable_path = Path(str(executable.get("path", "")))
    if not executable_path.is_file() or not os.access(executable_path, os.X_OK):
        return {
            "tool_name": tool_name,
            "executable_name": executable_name,
            "command": [str(executable_path), "--help"],
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"executable is not runnable: {executable_path}",
        }, 400

    try:
        result = subprocess.run(
            [str(executable_path), "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "tool_name": tool_name,
            "executable_name": executable_name,
            "command": [str(executable_path), "--help"],
            "return_code": None,
            "stdout": _truncate_output(exc.stdout or ""),
            "stderr": _truncate_output(exc.stderr or ""),
            "error": "help command timed out.",
        }, 200
    except OSError as exc:
        return {
            "tool_name": tool_name,
            "executable_name": executable_name,
            "command": [str(executable_path), "--help"],
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"unable to run help command: {exc}",
        }, 400

    return {
        "tool_name": tool_name,
        "executable_name": executable_name,
        "command": [str(executable_path), "--help"],
        "return_code": result.returncode,
        "stdout": _truncate_output(result.stdout),
        "stderr": _truncate_output(result.stderr),
        "error": None,
    }, 200


def _parse_uv_tool_list(output: str) -> list[UvTool]:
    tools: list[UvTool] = []
    current_tool: UvTool | None = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        executable_match = EXECUTABLE_LINE_RE.match(line)
        if executable_match and current_tool is not None:
            current_tool.executables.append(
                UvToolExecutable(
                    name=executable_match.group("name"),
                    path=executable_match.group("path"),
                )
            )
            continue

        tool_match = TOOL_LINE_RE.match(line)
        if not tool_match:
            continue

        current_tool = UvTool(
            name=tool_match.group("name"),
            version=tool_match.group("version"),
            environment_path=tool_match.group("environment_path"),
        )
        _populate_tool_metadata(current_tool, tool_match.group("meta"))
        tools.append(current_tool)

    return tools


def _populate_tool_metadata(tool: UvTool, meta: str) -> None:
    for item in META_RE.findall(meta):
        if item.startswith("required: "):
            tool.required_specifier = item.removeprefix("required: ").strip()
        elif item.startswith("CPython ") or item.startswith("PyPy "):
            tool.python_version = item.strip()


def _populate_editable_metadata(uv_bin: str, tool: UvTool) -> None:
    python_path = _tool_python_path(tool.environment_path)
    if not python_path.is_file():
        tool.inspection_error = f"Python executable not found: {python_path}"
        return

    try:
        result = subprocess.run(
            [uv_bin, "pip", "list", "--python", str(python_path), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        tool.inspection_error = f"Unable to inspect tool environment: {exc}"
        return

    if result.returncode != 0:
        tool.inspection_error = (
            result.stderr.strip() or result.stdout.strip() or "uv pip list failed."
        )
        return

    try:
        packages = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        tool.inspection_error = f"Unable to parse uv pip list JSON: {exc}"
        return

    if not isinstance(packages, list):
        tool.inspection_error = "uv pip list returned an unexpected payload."
        return

    editable_packages = [
        {
            "name": str(package.get("name", "")),
            "version": str(package.get("version", "")),
            "editable_project_location": str(
                package.get("editable_project_location", "")
            ),
        }
        for package in packages
        if isinstance(package, dict) and package.get("editable_project_location")
    ]
    tool.editable_packages = editable_packages

    normalized_tool_name = _normalize_package_name(tool.name)
    matching_package = next(
        (
            package
            for package in editable_packages
            if _normalize_package_name(package["name"]) == normalized_tool_name
        ),
        None,
    )
    if matching_package is None and len(editable_packages) == 1:
        matching_package = editable_packages[0]

    if matching_package is not None:
        tool.is_editable = True
        tool.editable_project_location = matching_package["editable_project_location"]


def _tool_python_path(environment_path: str) -> Path:
    env_path = Path(environment_path)
    windows_path = env_path / "Scripts" / "python.exe"
    if windows_path.is_file():
        return windows_path
    return env_path / "bin" / "python"


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _truncate_output(output: str) -> str:
    if len(output) <= HELP_OUTPUT_MAX_CHARS:
        return output
    return output[:HELP_OUTPUT_MAX_CHARS] + "\n[output truncated]"


def _resolve_uv_binary() -> str | None:
    for candidate in _preferred_uv_binary_candidates():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("uv")


def _preferred_uv_binary_candidates() -> list[Path]:
    candidates: list[Path] = []

    if InstallationConfig.exists():
        try:
            workspace = Path(InstallationConfig.load().workspace_path)
        except (OSError, ValueError, TypeError):
            workspace = None
        if workspace is not None:
            candidates.extend(
                [
                    workspace / ".venv" / "bin" / "uv",
                    workspace / "cli" / ".venv" / "bin" / "uv",
                    workspace / "agent" / ".venv" / "bin" / "uv",
                ]
            )

    candidates.extend(
        [
            Path.home() / ".local" / "bin" / "uv",
            Path("/opt/homebrew/bin/uv"),
            Path("/usr/local/bin/uv"),
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
