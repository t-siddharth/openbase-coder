from __future__ import annotations

import importlib

setup_cli = importlib.import_module("openbase_coder_cli.cli.setup")


def test_ensure_codex_home_default_files_creates_missing_files(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    instructions = workspace / "instructions"
    instructions.mkdir(parents=True)
    codex_home = tmp_path / "codex_home"
    targets = tuple(
        (resource_name, codex_home / resource_name)
        for resource_name, _target_path in setup_cli.CODEX_HOME_DEFAULT_FILES
    )
    for resource_name, _target_path in targets:
        (instructions / resource_name).write_text(
            f"default {resource_name}\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(setup_cli, "CODEX_HOME_DIR", codex_home)
    monkeypatch.setattr(setup_cli, "CODEX_HOME_DEFAULT_FILES", targets)

    setup_cli._ensure_codex_home_default_files(str(workspace))

    for resource_name, target_path in targets:
        assert target_path.read_text(encoding="utf-8") == f"default {resource_name}\n"


def test_ensure_codex_home_default_files_preserves_existing_files(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    instructions = workspace / "instructions"
    instructions.mkdir(parents=True)
    codex_home = tmp_path / "codex_home"
    existing_path = codex_home / "AGENTS.md"
    missing_path = codex_home / "VOICE_INSTRUCTIONS.md"
    existing_path.parent.mkdir(parents=True)
    existing_path.write_text("custom instructions\n", encoding="utf-8")
    (instructions / "AGENTS.md").write_text("default agents\n", encoding="utf-8")
    (instructions / "VOICE_INSTRUCTIONS.md").write_text(
        "default voice\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_cli, "CODEX_HOME_DIR", codex_home)
    monkeypatch.setattr(
        setup_cli,
        "CODEX_HOME_DEFAULT_FILES",
        (
            ("AGENTS.md", existing_path),
            ("VOICE_INSTRUCTIONS.md", missing_path),
        ),
    )

    setup_cli._ensure_codex_home_default_files(str(workspace))

    assert existing_path.read_text(encoding="utf-8") == "custom instructions\n"
    assert missing_path.read_text(encoding="utf-8") == "default voice\n"


def test_ensure_codex_home_default_files_skips_missing_sources(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    codex_home = tmp_path / "codex_home"
    target_path = codex_home / "AGENTS.md"
    monkeypatch.setattr(setup_cli, "CODEX_HOME_DIR", codex_home)
    monkeypatch.setattr(
        setup_cli,
        "CODEX_HOME_DEFAULT_FILES",
        (("AGENTS.md", target_path),),
    )

    setup_cli._ensure_codex_home_default_files(str(workspace))

    assert not target_path.exists()


def test_symlink_codex_home_skills_links_workspace_skills(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    skill = workspace / "skills" / "skills" / "sample-skill"
    codex_home = tmp_path / "codex_home"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setattr(setup_cli, "CODEX_HOME_DIR", codex_home)

    setup_cli._symlink_codex_home_skills(str(workspace))

    target = codex_home / "skills" / "sample-skill"
    assert target.is_symlink()
    assert target.resolve() == skill.resolve()


def test_symlink_codex_home_skills_replaces_existing_symlink(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    skill = workspace / "skills" / "skills" / "sample-skill"
    stale_skill = tmp_path / "stale-skill"
    codex_home = tmp_path / "codex_home"
    target = codex_home / "skills" / "sample-skill"
    skill.mkdir(parents=True)
    stale_skill.mkdir()
    target.parent.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Sample\n", encoding="utf-8")
    target.symlink_to(stale_skill)
    monkeypatch.setattr(setup_cli, "CODEX_HOME_DIR", codex_home)

    setup_cli._symlink_codex_home_skills(str(workspace))

    assert target.is_symlink()
    assert target.resolve() == skill.resolve()


def test_symlink_codex_home_skills_preserves_real_directories(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    skill = workspace / "skills" / "skills" / "sample-skill"
    codex_home = tmp_path / "codex_home"
    target = codex_home / "skills" / "sample-skill"
    skill.mkdir(parents=True)
    target.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Sample\n", encoding="utf-8")
    (target / "SKILL.md").write_text("# Custom\n", encoding="utf-8")
    monkeypatch.setattr(setup_cli, "CODEX_HOME_DIR", codex_home)

    setup_cli._symlink_codex_home_skills(str(workspace))

    assert not target.is_symlink()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# Custom\n"


def test_workspace_skill_sources_supports_direct_skill_dirs(tmp_path) -> None:
    source_root = tmp_path / "skills"
    direct_skill = source_root / "direct-skill"
    nested_skill = source_root / "skills" / "nested-skill"
    direct_skill.mkdir(parents=True)
    nested_skill.mkdir(parents=True)
    (direct_skill / "SKILL.md").write_text("# Direct\n", encoding="utf-8")
    (nested_skill / "SKILL.md").write_text("# Nested\n", encoding="utf-8")

    assert setup_cli._workspace_skill_sources(source_root) == [
        nested_skill,
        direct_skill,
    ]


def test_build_console_does_not_sync_plugin_generated_files(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    console_dir = workspace / "console"
    generated_registry = console_dir / "src" / "generated" / "pluginRegistry.ts"
    console_dir.mkdir(parents=True)
    commands = []

    def fake_run_workspace_package_command(workspace_dir, package_dir, *args):
        commands.append((workspace_dir, package_dir, args))
        return True

    def fail_if_plugin_registry_is_loaded():
        raise AssertionError("setup should not sync plugin console integration")

    monkeypatch.setattr(
        setup_cli,
        "run_workspace_package_command",
        fake_run_workspace_package_command,
    )
    monkeypatch.setattr(setup_cli, "load_registry", fail_if_plugin_registry_is_loaded, raising=False)

    setup_cli._build_console(str(workspace))

    assert commands == [
        (workspace, console_dir, ("install",)),
        (workspace, console_dir, ("run", "build")),
    ]
    assert not generated_registry.exists()
