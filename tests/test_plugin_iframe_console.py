from __future__ import annotations

import json
from pathlib import Path

import pytest

from openbase_coder_cli.plugins.console import sync_console_integration
from openbase_coder_cli.plugins.manager import add_plugin
from openbase_coder_cli.plugins.models import (
    ConsolePageSpec,
    PluginCapabilities,
    PluginRecord,
    PluginRegistry,
)
from openbase_coder_cli.plugins.spec import normalize_capabilities


def test_normalize_capabilities_accepts_iframe_console_page():
    capabilities = normalize_capabilities(
        {
            "console_pages": [
                {
                    "key": "dashboard",
                    "title": "Dashboard",
                    "asset_dir": "web",
                    "entrypoint": "index.html",
                }
            ]
        },
        "example",
    )

    page = capabilities.console_pages[0]
    assert page.render == "iframe"
    assert page.asset_dir == "web"
    assert page.route == "/dashboard/plugins/example/dashboard"


def test_sync_console_integration_copies_iframe_assets(monkeypatch, tmp_path: Path):
    source = tmp_path / "plugin"
    assets = source / "web"
    assets.mkdir(parents=True)
    (assets / "index.html").write_text("<h1>Plugin</h1>", encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    assets_root = tmp_path / "assets"
    monkeypatch.setattr(
        "openbase_coder_cli.plugins.store.PLUGIN_CONSOLE_REGISTRY_PATH",
        registry_path,
    )
    monkeypatch.setattr(
        "openbase_coder_cli.plugins.console.PLUGIN_CONSOLE_ASSETS_DIR",
        assets_root,
    )

    registry = PluginRegistry(
        plugins=[
            PluginRecord(
                plugin_id="example",
                display_name="Example",
                version="0.1.0",
                package_name="example",
                source_type="local",
                source=str(source),
                source_path=str(source),
                entrypoint_name="example",
                entrypoint_value="example.spec:get_plugin_spec",
                requirement=f"-e {source}",
                capabilities=PluginCapabilities(
                    console_pages=[
                        ConsolePageSpec(
                            key="dashboard",
                            title="Dashboard",
                            route="/dashboard/plugins/example/dashboard",
                            render="iframe",
                            asset_dir="web",
                        )
                    ]
                ),
            )
        ]
    )

    sync_console_integration(registry, workspace_path=None)

    copied = assets_root / "example" / "dashboard" / "index.html"
    assert copied.read_text(encoding="utf-8") == "<h1>Plugin</h1>"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    page = payload["pages"][0]["pages"][0]
    assert page["render"] == "iframe"
    assert page["iframe_url"] == (
        "/openbase-plugin-assets/example/dashboard/index.html"
    )


def test_standalone_mode_rejects_legacy_component_console_pages(monkeypatch):
    record = PluginRecord(
        plugin_id="legacy",
        display_name="Legacy",
        version="0.1.0",
        package_name="legacy",
        source_type="local",
        source="/tmp/legacy",
        source_path="/tmp/legacy",
        entrypoint_name="legacy",
        entrypoint_value="legacy.spec:get_plugin_spec",
        requirement="-e /tmp/legacy",
        capabilities=PluginCapabilities(
            console_pages=[
                ConsolePageSpec(
                    key="page",
                    title="Page",
                    route="/dashboard/plugins/legacy/page",
                    import_module="legacy/Page",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        "openbase_coder_cli.plugins.manager.load_registry", lambda: PluginRegistry()
    )
    monkeypatch.setattr(
        "openbase_coder_cli.plugins.manager._build_record", lambda **_kwargs: record
    )
    monkeypatch.setattr(
        "openbase_coder_cli.plugins.manager._standalone_mode", lambda: True
    )
    monkeypatch.setattr(
        "openbase_coder_cli.plugins.manager.uninstall_package", lambda _name: None
    )

    with pytest.raises(Exception, match="iframe console pages only"):
        add_plugin("/tmp/legacy", ref=None)
