from __future__ import annotations

import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

import click

from openbase_coder_cli.paths import PLUGIN_SOURCES_DIR

_GITHUB_HTTPS_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
_GITHUB_SSH_RE = re.compile(
    r"^git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?$"
)
_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


@dataclass
class ResolvedPluginSource:
    source_type: str
    original: str
    local_path: Path
    github_url: str = ""
    ref: str = ""
    commit_sha: str = ""


def _parse_github_source(source: str) -> tuple[str, str] | None:
    https_match = _GITHUB_HTTPS_RE.match(source)
    if https_match:
        return https_match.group("owner"), https_match.group("repo")

    ssh_match = _GITHUB_SSH_RE.match(source)
    if ssh_match:
        return ssh_match.group("owner"), ssh_match.group("repo")

    return None


def _default_branch(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    value = result.stdout.strip()
    if "/" not in value:
        raise click.ClickException("Unable to determine default branch")
    return value.rsplit("/", 1)[-1]


def _resolve_commit(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def resolve_source(source: str, ref: str | None) -> ResolvedPluginSource:
    possible_path = Path(source).expanduser().resolve()
    if possible_path.is_dir():
        if not (possible_path / "pyproject.toml").is_file():
            raise click.ClickException(
                f"Local plugin path must contain pyproject.toml: {possible_path}"
            )
        return ResolvedPluginSource(
            source_type="local",
            original=source,
            local_path=possible_path,
        )

    parsed = _parse_github_source(source)
    if not parsed:
        raise click.ClickException(
            "Plugin source must be a local directory or a GitHub URL"
        )

    owner, repo = parsed
    github_url = f"https://github.com/{owner}/{repo}.git"

    target_dir = PLUGIN_SOURCES_DIR / f"{owner}__{repo}"
    PLUGIN_SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    if target_dir.is_dir():
        subprocess.run(["git", "-C", str(target_dir), "fetch", "origin"], check=True)
    else:
        subprocess.run(["git", "clone", github_url, str(target_dir)], check=True)

    branch_or_ref = ref or _default_branch(target_dir)
    subprocess.run(
        ["git", "-C", str(target_dir), "checkout", branch_or_ref], check=True
    )
    if not _COMMIT_RE.match(branch_or_ref):
        subprocess.run(["git", "-C", str(target_dir), "pull", "--ff-only"], check=True)
    commit_sha = _resolve_commit(target_dir)

    return ResolvedPluginSource(
        source_type="github",
        original=source,
        local_path=target_dir,
        github_url=github_url,
        ref=branch_or_ref,
        commit_sha=commit_sha,
    )


def inspect_source(source_path: Path) -> tuple[str, str, str]:
    pyproject_path = source_path / "pyproject.toml"
    if not pyproject_path.is_file():
        raise click.ClickException(f"Missing pyproject.toml in {source_path}")

    data = tomllib.loads(pyproject_path.read_text())
    project = data.get("project", {})
    package_name = str(project.get("name", "")).strip()
    if not package_name:
        raise click.ClickException("Plugin pyproject.toml is missing project.name")

    entry_points = project.get("entry-points", {})
    group = entry_points.get("openbase_coder.plugins", {})
    if not isinstance(group, dict) or not group:
        raise click.ClickException(
            'Plugin pyproject.toml must declare [project.entry-points."openbase_coder.plugins"]'
        )

    if len(group) != 1:
        raise click.ClickException(
            "Each plugin package must declare exactly one openbase_coder.plugins entry point"
        )

    entrypoint_name, entrypoint_value = next(iter(group.items()))
    return package_name, str(entrypoint_name), str(entrypoint_value)
