"""Skill file management API views."""

from __future__ import annotations

import shutil
from pathlib import Path

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from openbase_coder_cli.paths import CODEX_HOME_DIR


def _home_skills_dir() -> Path:
    return Path.home() / ".agents" / "skills"


def _voice_coder_skills_dir() -> Path:
    return CODEX_HOME_DIR / "skills"


def _skills_dir(project_path: str | None, scope: str = "home") -> Path:
    """Return the skills directory for a project or global scope."""
    if project_path:
        return Path(project_path).expanduser().resolve() / ".agents" / "skills"
    if scope in {"voice_coder", "openbase_codex"}:
        return _voice_coder_skills_dir()
    if scope in {"home", "normal_codex"}:
        return _home_skills_dir()
    raise ValueError("invalid skill scope")


def _skill_scope_payload() -> list[dict[str, str]]:
    return [
        {
            "key": "home",
            "label": "Normal Codex skills",
            "skills_dir": str(_home_skills_dir()),
        },
        {
            "key": "voice_coder",
            "label": "Openbase Codex skills",
            "skills_dir": str(_voice_coder_skills_dir()),
        },
    ]


def _list_skill_entries(skills_root: Path) -> list[dict[str, str]]:
    skills = []
    if skills_root.is_dir():
        for child in sorted(skills_root.iterdir()):
            skill_file = child / "SKILL.md"
            if child.is_dir() and skill_file.is_file():
                entry = {
                    "name": child.name,
                    "path": str(skill_file),
                    "dir_path": str(child),
                }
                if child.is_symlink():
                    entry["source_dir_path"] = str(child.resolve())
                if child.is_symlink() or skill_file.is_symlink():
                    entry["source_path"] = str(skill_file.resolve())
                skills.append(entry)
    return skills


def _skill_file(skills_root: Path, skill_name: str) -> Path:
    relative = Path(skill_name)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        raise ValueError("invalid skill name")
    return skills_root / relative / "SKILL.md"


def _skill_payload(skill_file: Path, skill_name: str) -> dict[str, str]:
    payload = {
        "path": str(skill_file),
        "name": skill_name,
        "dir_path": str(skill_file.parent),
    }
    if skill_file.parent.is_symlink():
        payload["source_dir_path"] = str(skill_file.parent.resolve())
    if skill_file.parent.is_symlink() or skill_file.is_symlink():
        payload["source_path"] = str(skill_file.resolve())
    return payload


def _same_resolved_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve(strict=True) == right.resolve(strict=True)
    except FileNotFoundError:
        return left.resolve(strict=False) == right.resolve(strict=False)


def _symlink_skill_between_scopes(
    *,
    skill_name: str,
    source_scope: str,
    target_scope: str,
) -> dict[str, str | bool]:
    source_root = _skills_dir(None, source_scope)
    target_root = _skills_dir(None, target_scope)
    source_skill_file = _skill_file(source_root, skill_name)
    target_skill_file = _skill_file(target_root, skill_name)
    source_dir = source_skill_file.parent
    target_dir = target_skill_file.parent

    if source_scope == target_scope:
        raise ValueError("source and target scopes must differ")
    if not source_skill_file.is_file():
        raise FileNotFoundError(f"Skill '{skill_name}' was not found in {source_root}")

    source_link_target = source_dir
    if target_dir.exists() or target_dir.is_symlink():
        if target_dir.is_symlink() and _same_resolved_path(
            target_dir, source_link_target
        ):
            return {
                "name": skill_name,
                "created": False,
                "source_scope": source_scope,
                "target_scope": target_scope,
                "source_dir": str(source_link_target),
                "target_dir": str(target_dir),
                "target_path": str(target_skill_file),
            }
        raise FileExistsError(f"Skill '{skill_name}' already exists in {target_root}")

    target_root.mkdir(parents=True, exist_ok=True)
    target_dir.symlink_to(source_link_target, target_is_directory=True)
    return {
        "name": skill_name,
        "created": True,
        "source_scope": source_scope,
        "target_scope": target_scope,
        "source_dir": str(source_link_target),
        "target_dir": str(target_dir),
        "target_path": str(target_skill_file),
    }


@api_view(["GET", "POST"])
def skills_list(request):
    """List skills or create a new one.

    Query params:
        path: project directory (omit for global skills)
    """
    project_path = request.query_params.get("path", "").strip() or None
    scope = request.query_params.get("scope", "home").strip()
    try:
        skills_root = _skills_dir(project_path, scope)
    except ValueError:
        return Response(
            {"error": "invalid skill scope"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "POST":
        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"error": "name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            skill_file = _skill_file(skills_root, name)
        except ValueError:
            return Response(
                {"error": "invalid skill name"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if skill_file.exists():
            return Response(
                {"error": f"Skill '{name}' already exists"},
                status=status.HTTP_409_CONFLICT,
            )
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        content = request.data.get(
            "content", f"---\nname: {name}\ndescription: \n---\n\n"
        )
        skill_file.write_text(content, encoding="utf-8")
        return Response(
            {"name": name, "path": str(skill_file)},
            status=status.HTTP_201_CREATED,
        )

    if project_path:
        return Response(
            {"skills": _list_skill_entries(skills_root), "skills_dir": str(skills_root)}
        )

    sections = []
    for scope_info in _skill_scope_payload():
        root = Path(scope_info["skills_dir"])
        sections.append({**scope_info, "skills": _list_skill_entries(root)})
    return Response(
        {
            "skills": sections[0]["skills"],
            "skills_dir": sections[0]["skills_dir"],
            "sections": sections,
        }
    )


@api_view(["POST"])
def skills_symlink(request):
    """Symlink a global skill between normal Codex and Openbase Codex homes."""
    skill_name = request.data.get("name", "").strip()
    source_scope = request.data.get("source_scope", "").strip()
    target_scope = request.data.get("target_scope", "").strip()
    if not skill_name or not source_scope or not target_scope:
        return Response(
            {"error": "name, source_scope, and target_scope are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_scopes = {"home", "normal_codex", "voice_coder", "openbase_codex"}
    if source_scope not in allowed_scopes or target_scope not in allowed_scopes:
        return Response(
            {"error": "invalid skill scope"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        _skill_file(_skills_dir(None, source_scope), skill_name)
        result = _symlink_skill_between_scopes(
            skill_name=skill_name,
            source_scope=source_scope,
            target_scope=target_scope,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except FileNotFoundError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except FileExistsError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(
        result,
        status=status.HTTP_201_CREATED if result["created"] else status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "DELETE"])
def skill_detail(request, skill_name):
    """Read, write, or delete a single skill's SKILL.md.

    Query params:
        path: project directory (omit for global skills)
    """
    project_path = request.query_params.get("path", "").strip() or None
    scope = request.query_params.get("scope", "home").strip()
    try:
        skill_file = _skill_file(_skills_dir(project_path, scope), skill_name)
    except ValueError:
        return Response(
            {"error": "invalid skill name or scope"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "DELETE":
        skill_dir = skill_file.parent
        if not skill_dir.is_dir():
            return Response(
                {"error": f"Skill '{skill_name}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if skill_dir.is_symlink():
            skill_dir.unlink()
        else:
            shutil.rmtree(skill_dir)
        return Response({"success": True})

    if request.method == "PUT":
        content = request.data.get("content", "")
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(content, encoding="utf-8")
        return Response({"content": content, "path": str(skill_file)})

    # GET
    if skill_file.exists():
        content = skill_file.read_text(encoding="utf-8")
    else:
        content = ""
    return Response({"content": content, **_skill_payload(skill_file, skill_name)})
