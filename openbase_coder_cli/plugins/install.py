from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which


def _installer_command() -> list[str]:
    uv_bin = which("uv")
    if uv_bin:
        return [uv_bin, "pip", "install", "--python", sys.executable]
    return [sys.executable, "-m", "pip", "install"]


def _uninstaller_command() -> list[str]:
    uv_bin = which("uv")
    if uv_bin:
        return [uv_bin, "pip", "uninstall", "--python", sys.executable]
    return [sys.executable, "-m", "pip", "uninstall"]


def install_local_editable(path: Path) -> str:
    subprocess.run(
        [*_installer_command(), "-e", str(path)],
        check=True,
    )
    return f"-e {path}"


def install_github_pinned(url: str, commit_sha: str) -> str:
    requirement = f"git+{url}@{commit_sha}"
    subprocess.run(
        [*_installer_command(), requirement],
        check=True,
    )
    return requirement


def uninstall_package(package_name: str) -> None:
    subprocess.run(
        [*_uninstaller_command(), "-y", package_name],
        check=False,
    )
