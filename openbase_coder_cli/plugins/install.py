from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which

import click


def _uv_binary() -> str:
    uv_bin = which("uv")
    if not uv_bin:
        raise click.ClickException("'uv' is required for plugin installation")
    return uv_bin


def install_local_editable(path: Path) -> str:
    uv_bin = _uv_binary()
    subprocess.run(
        [uv_bin, "pip", "install", "--python", sys.executable, "-e", str(path)],
        check=True,
    )
    return f"-e {path}"


def install_github_pinned(url: str, commit_sha: str) -> str:
    requirement = f"git+{url}@{commit_sha}"
    uv_bin = _uv_binary()
    subprocess.run(
        [uv_bin, "pip", "install", "--python", sys.executable, requirement],
        check=True,
    )
    return requirement


def uninstall_package(package_name: str) -> None:
    uv_bin = _uv_binary()
    subprocess.run(
        [uv_bin, "pip", "uninstall", "--python", sys.executable, "-y", package_name],
        check=False,
    )
