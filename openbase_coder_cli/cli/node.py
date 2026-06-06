from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import click


def run_workspace_package_command(workspace_dir: Path, package_dir: Path, *args: str) -> bool:
    """Run a package-manager command for a workspace package."""
    package_manager = _resolve_package_manager(workspace_dir, package_dir)
    if package_manager is None:
        click.echo("'npm' or 'pnpm' not found on PATH, skipping console build.")
        return False

    executable, command_prefix = package_manager
    subprocess.run(
        [executable, *command_prefix, *args],
        cwd=str(package_dir),
        check=True,
    )
    return True


def _resolve_package_manager(
    workspace_dir: Path,
    package_dir: Path,
) -> tuple[str, tuple[str, ...]] | None:
    if _uses_pnpm_workspace(workspace_dir, package_dir):
        pnpm_bin = _which_node_binary("pnpm")
        if pnpm_bin:
            return pnpm_bin, ()

    npm_bin = _which_node_binary("npm")
    if npm_bin:
        return npm_bin, ()

    pnpm_bin = _which_node_binary("pnpm")
    if pnpm_bin:
        return pnpm_bin, ()

    return None


def _uses_pnpm_workspace(workspace_dir: Path, package_dir: Path) -> bool:
    if (workspace_dir / "pnpm-workspace.yaml").is_file() or (
        workspace_dir / "pnpm-lock.yaml"
    ).is_file():
        return True

    package_json = package_dir / "package.json"
    if not package_json.is_file():
        return False

    try:
        return '"workspace:' in package_json.read_text(encoding="utf-8")
    except OSError:
        return False


def _which_node_binary(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved

    candidates = []
    if pnpm_home := os.environ.get("PNPM_HOME"):
        candidates.append(Path(pnpm_home) / name)
    candidates.extend(
        [
            Path.home() / "Library" / "pnpm" / name,
            Path("/opt/homebrew/bin") / name,
            Path("/usr/local/bin") / name,
        ]
    )

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None
