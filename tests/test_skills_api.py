from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OPENBASE_CODER_CLI_SECRET_KEY", "test-secret")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openbase_coder_cli.config.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

django.setup()

from openbase_coder_cli.openbase_coder_cli_app import views  # noqa: E402


def _request(method: str, path: str, data: dict | None = None):
    factory = APIRequestFactory()
    request = getattr(factory, method)(path, data or {}, format="json")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return request


def _write_skill(root: Path, name: str, content: str = "instructions") -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


def _patch_skill_homes(
    monkeypatch,
    normal_home: Path,
    openbase_home: Path,
    claude_home: Path | None = None,
) -> None:
    monkeypatch.setattr(views, "_home_skills_dir", lambda: normal_home / "skills")
    monkeypatch.setattr(views, "CODEX_HOME_DIR", openbase_home)
    monkeypatch.setattr(
        views,
        "OPENBASE_CLAUDE_CONFIG_DIR",
        claude_home or normal_home.parent / "openbase-claude",
    )


def test_skills_list_uses_normal_and_openbase_codex_homes(tmp_path: Path, monkeypatch):
    normal_home = tmp_path / "normal-codex"
    openbase_home = tmp_path / "openbase-codex"
    claude_home = tmp_path / "openbase-claude"
    _write_skill(normal_home, "normal-skill")
    _write_skill(openbase_home, "openbase-skill")
    _write_skill(claude_home, "claude-skill")

    _patch_skill_homes(monkeypatch, normal_home, openbase_home, claude_home)

    response = views.skills_list(_request("get", "/api/skills/"))

    assert response.status_code == 200
    sections = {section["key"]: section for section in response.data["sections"]}
    assert sections["home"]["label"] == "Normal Codex skills"
    assert sections["home"]["skills_dir"] == str(normal_home / "skills")
    assert [skill["name"] for skill in sections["home"]["skills"]] == ["normal-skill"]
    assert sections["voice_coder"]["label"] == "Openbase Codex skills"
    assert sections["voice_coder"]["skills_dir"] == str(openbase_home / "skills")
    assert [skill["name"] for skill in sections["voice_coder"]["skills"]] == [
        "openbase-skill"
    ]
    assert sections["claude"]["label"] == "Openbase Claude skills"
    assert sections["claude"]["skills_dir"] == str(claude_home / "skills")
    assert [skill["name"] for skill in sections["claude"]["skills"]] == [
        "claude-skill"
    ]


def test_skills_symlink_links_normal_skill_to_openbase_codex(
    tmp_path: Path, monkeypatch
):
    normal_home = tmp_path / "normal-codex"
    openbase_home = tmp_path / "openbase-codex"
    source_dir = _write_skill(normal_home, "shared-skill")

    _patch_skill_homes(monkeypatch, normal_home, openbase_home)

    response = views.skills_symlink(
        _request(
            "post",
            "/api/skills/symlink/",
            {
                "name": "shared-skill",
                "source_scope": "home",
                "target_scope": "voice_coder",
            },
        )
    )

    target_dir = openbase_home / "skills" / "shared-skill"
    assert response.status_code == 201
    assert response.data["created"] is True
    assert response.data["source_dir"] == str(source_dir.resolve())
    assert target_dir.is_symlink()
    assert target_dir.resolve() == source_dir.resolve()
    assert (target_dir / "SKILL.md").read_text(encoding="utf-8") == "instructions"


def test_skills_symlink_returns_ok_when_link_already_exists(
    tmp_path: Path, monkeypatch
):
    normal_home = tmp_path / "normal-codex"
    openbase_home = tmp_path / "openbase-codex"
    source_dir = _write_skill(normal_home, "shared-skill")
    target_dir = openbase_home / "skills" / "shared-skill"
    target_dir.parent.mkdir(parents=True)
    target_dir.symlink_to(source_dir, target_is_directory=True)

    _patch_skill_homes(monkeypatch, normal_home, openbase_home)

    response = views.skills_symlink(
        _request(
            "post",
            "/api/skills/symlink/",
            {
                "name": "shared-skill",
                "source_scope": "home",
                "target_scope": "voice_coder",
            },
        )
    )

    assert response.status_code == 200
    assert response.data["created"] is False


def test_skills_symlink_rejects_existing_non_link_target(tmp_path: Path, monkeypatch):
    normal_home = tmp_path / "normal-codex"
    openbase_home = tmp_path / "openbase-codex"
    _write_skill(normal_home, "shared-skill", "normal")
    _write_skill(openbase_home, "shared-skill", "openbase")

    _patch_skill_homes(monkeypatch, normal_home, openbase_home)

    response = views.skills_symlink(
        _request(
            "post",
            "/api/skills/symlink/",
            {
                "name": "shared-skill",
                "source_scope": "home",
                "target_scope": "voice_coder",
            },
        )
    )

    assert response.status_code == 409
    assert "already exists" in response.data["error"]
    assert not (openbase_home / "skills" / "shared-skill").is_symlink()


def test_skill_delete_unlinks_symlink_without_deleting_source(
    tmp_path: Path, monkeypatch
):
    normal_home = tmp_path / "normal-codex"
    openbase_home = tmp_path / "openbase-codex"
    source_dir = _write_skill(normal_home, "shared-skill")
    target_dir = openbase_home / "skills" / "shared-skill"
    target_dir.parent.mkdir(parents=True)
    target_dir.symlink_to(source_dir, target_is_directory=True)

    _patch_skill_homes(monkeypatch, normal_home, openbase_home)

    request = _request(
        "delete",
        "/api/skills/shared-skill/?scope=voice_coder",
    )
    response = views.skill_detail(request, "shared-skill")

    assert response.status_code == 200
    assert not target_dir.exists()
    assert source_dir.is_dir()
    assert (source_dir / "SKILL.md").read_text(encoding="utf-8") == "instructions"


def test_skills_symlink_preserves_existing_source_symlink_chain(
    tmp_path: Path, monkeypatch
):
    normal_home = tmp_path / "normal-codex"
    openbase_home = tmp_path / "openbase-codex"
    real_skill = tmp_path / "Developer" / "skills" / "shared-skill"
    real_skill.mkdir(parents=True)
    (real_skill / "SKILL.md").write_text("real instructions", encoding="utf-8")
    source_dir = normal_home / "skills" / "shared-skill"
    source_dir.parent.mkdir(parents=True)
    source_dir.symlink_to(real_skill, target_is_directory=True)
    _patch_skill_homes(monkeypatch, normal_home, openbase_home)

    response = views.skills_symlink(
        _request(
            "post",
            "/api/skills/symlink/",
            {
                "name": "shared-skill",
                "source_scope": "home",
                "target_scope": "voice_coder",
            },
        )
    )

    target_dir = openbase_home / "skills" / "shared-skill"
    assert response.status_code == 201
    assert response.data["source_dir"] == str(source_dir)
    assert target_dir.is_symlink()
    assert os.readlink(target_dir) == str(source_dir)
    assert target_dir.resolve() == real_skill.resolve()
