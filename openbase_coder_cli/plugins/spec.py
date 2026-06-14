from __future__ import annotations

import importlib.metadata as metadata
import re
from collections.abc import Callable

import click

from .models import (
    BootstrapperSpec,
    ConsolePageSpec,
    PluginCapabilities,
    ProjectViewSpec,
    SkillSpec,
    StackSpec,
)

_PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,62}$")


def _normalize_distribution_name(name: str) -> str:
    return name.replace("-", "_").lower()


def _as_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise click.ClickException(f"Plugin field '{field_name}' must be a string")
    return value.strip()


def _load_entrypoint_value(entrypoint: metadata.EntryPoint) -> dict:
    loaded = entrypoint.load()
    raw = loaded() if isinstance(loaded, Callable) else loaded
    if not isinstance(raw, dict):
        raise click.ClickException(
            f"Plugin entry point '{entrypoint.name}' must return a dict"
        )
    return raw


def load_plugin_spec(package_name: str, entrypoint_name: str) -> tuple[dict, str]:
    selected_entrypoint: metadata.EntryPoint | None = None
    for entrypoint in metadata.entry_points(group="openbase_coder.plugins"):
        dist_name = getattr(entrypoint.dist, "name", "")
        if _normalize_distribution_name(dist_name) != _normalize_distribution_name(
            package_name
        ):
            continue
        if entrypoint.name != entrypoint_name:
            continue
        selected_entrypoint = entrypoint
        break

    if not selected_entrypoint:
        raise click.ClickException(
            f"Could not find installed plugin entry point '{entrypoint_name}' "
            f"for package '{package_name}'"
        )

    raw = _load_entrypoint_value(selected_entrypoint)
    return raw, selected_entrypoint.value


def normalize_capabilities(raw_spec: dict, plugin_id: str) -> PluginCapabilities:
    cap_root = raw_spec.get("capabilities")
    if cap_root is None:
        cap_root = raw_spec
    if not isinstance(cap_root, dict):
        raise click.ClickException("Plugin capabilities must be an object")

    bootstrappers: list[BootstrapperSpec] = []
    for item in cap_root.get("bootstrappers", []):
        if not isinstance(item, dict):
            raise click.ClickException("bootstrapper entries must be objects")
        name = _as_string(item.get("name", ""), field_name="bootstrapper.name")
        handler = _as_string(
            item.get("handler", ""), field_name=f"bootstrapper[{name}].handler"
        )
        description = str(item.get("description", "")).strip()
        stack = str(item.get("stack", "")).strip()
        bootstrappers.append(
            BootstrapperSpec(
                name=name, handler=handler, description=description, stack=stack
            )
        )

    stacks: list[StackSpec] = []
    for item in cap_root.get("stacks", []):
        if not isinstance(item, dict):
            raise click.ClickException("stack entries must be objects")
        name = _as_string(item.get("name", ""), field_name="stack.name")
        stacks.append(
            StackSpec(name=name, description=str(item.get("description", "")).strip())
        )

    console_pages: list[ConsolePageSpec] = []
    for item in cap_root.get("console_pages", []):
        if not isinstance(item, dict):
            raise click.ClickException("console_pages entries must be objects")
        key = _as_string(item.get("key", ""), field_name="console_page.key")
        title = str(item.get("title", key)).strip() or key
        route = str(item.get("route", f"/dashboard/plugins/{plugin_id}/{key}")).strip()
        if not route.startswith("/"):
            route = "/" + route
        if not route.startswith("/dashboard"):
            raise click.ClickException(
                f"console page '{key}' route must start with '/dashboard'"
            )
        import_module = _as_string(
            item.get("import_module", ""),
            field_name=f"console_page[{key}].import_module",
        )
        export_name = str(item.get("export", "default")).strip() or "default"
        sidebar = bool(item.get("sidebar", True))
        console_pages.append(
            ConsolePageSpec(
                key=key,
                title=title,
                route=route,
                import_module=import_module,
                export=export_name,
                sidebar=sidebar,
            )
        )

    project_views: list[ProjectViewSpec] = []
    for item in cap_root.get("project_views", []):
        if not isinstance(item, dict):
            raise click.ClickException("project_views entries must be objects")
        stack = _as_string(item.get("stack", ""), field_name="project_view.stack")
        import_module = _as_string(
            item.get("import_module", ""),
            field_name=f"project_view[{stack}].import_module",
        )
        export_name = str(item.get("export", "default")).strip() or "default"
        title = str(item.get("title", stack)).strip() or stack
        project_views.append(
            ProjectViewSpec(
                stack=stack,
                import_module=import_module,
                export=export_name,
                title=title,
            )
        )

    skills: list[SkillSpec] = []
    for item in cap_root.get("skills", []):
        if not isinstance(item, dict):
            raise click.ClickException("skills entries must be objects")
        name = _as_string(item.get("name", ""), field_name="skill.name")
        source = _as_string(item.get("source", ""), field_name=f"skill[{name}].source")
        skills.append(SkillSpec(name=name, source=source))

    django_url_modules: list[str] = []
    for entry in cap_root.get("django_url_modules", []):
        django_url_modules.append(_as_string(entry, field_name="django_url_modules[]"))

    console_npm_packages: list[str] = []
    for entry in cap_root.get("console_npm_packages", []):
        console_npm_packages.append(
            _as_string(entry, field_name="console_npm_packages[]")
        )

    return PluginCapabilities(
        bootstrappers=bootstrappers,
        stacks=stacks,
        console_pages=console_pages,
        project_views=project_views,
        skills=skills,
        django_url_modules=django_url_modules,
        console_npm_packages=console_npm_packages,
    )


def normalize_plugin_header(raw_spec: dict) -> tuple[str, str, str]:
    plugin_id = _as_string(raw_spec.get("plugin_id", ""), field_name="plugin_id")
    if not _PLUGIN_ID_RE.match(plugin_id):
        raise click.ClickException(
            "plugin_id must be a slug matching [a-z][a-z0-9_-]{1,62}"
        )
    display_name = str(raw_spec.get("display_name", plugin_id)).strip() or plugin_id
    version = str(raw_spec.get("version", "0.0.0")).strip() or "0.0.0"
    return plugin_id, display_name, version
