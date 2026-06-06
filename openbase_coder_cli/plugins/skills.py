from __future__ import annotations

import shutil
from pathlib import Path

import click

from .models import PluginRecord
from .store import load_skills_ownership, save_skills_ownership

GLOBAL_SKILLS_DIR = Path.home() / ".claude" / "skills"


def _copy_skill_source(source_path: Path, target_dir: Path) -> None:
    if source_path.is_dir():
        shutil.copytree(source_path, target_dir)
        skill_md = target_dir / "SKILL.md"
        if not skill_md.is_file():
            raise click.ClickException(
                f"Skill directory missing SKILL.md after copy: {target_dir}"
            )
        return

    if source_path.is_file() and source_path.name == "SKILL.md":
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_dir / "SKILL.md")
        return

    raise click.ClickException(
        f"Skill source must be a directory or SKILL.md file: {source_path}"
    )


def sync_plugin_skills(plugin: PluginRecord) -> None:
    ownership = load_skills_ownership()

    # Remove previous targets owned by this plugin before re-syncing
    for target_name, owner in list(ownership.items()):
        if owner != plugin.plugin_id:
            continue
        shutil.rmtree(GLOBAL_SKILLS_DIR / target_name, ignore_errors=True)
        ownership.pop(target_name, None)

    GLOBAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    source_root = Path(plugin.source_path)
    for skill in plugin.capabilities.skills:
        source_path = source_root / skill.source
        if not source_path.exists():
            raise click.ClickException(
                f"Skill source not found for {plugin.plugin_id}/{skill.name}: {source_path}"
            )

        target_name = f"{plugin.plugin_id}__{skill.name}"
        target_dir = GLOBAL_SKILLS_DIR / target_name
        if target_dir.exists():
            shutil.rmtree(target_dir)

        _copy_skill_source(source_path, target_dir)
        ownership[target_name] = plugin.plugin_id

    save_skills_ownership(ownership)


def remove_plugin_skills(plugin_id: str) -> None:
    ownership = load_skills_ownership()

    for target_name, owner in list(ownership.items()):
        if owner != plugin_id:
            continue
        shutil.rmtree(GLOBAL_SKILLS_DIR / target_name, ignore_errors=True)
        ownership.pop(target_name, None)

    save_skills_ownership(ownership)
