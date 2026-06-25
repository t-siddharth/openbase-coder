# plugins

Manage Openbase plugins installed into the local CLI runtime.

## Usage

```bash
openbase-coder plugins COMMAND [ARGS]
```

## Subcommands

| Subcommand | Description |
|---|---|
| `add SOURCE [--ref REF]` | Install a plugin from local repo path or GitHub URL |
| `list` | List installed plugins |
| `show PLUGIN_ID` | Show a plugin's declared capabilities |
| `remove PLUGIN_ID` | Uninstall a plugin |
| `update [PLUGIN_ID] [--ref REF]` | Update one plugin or all plugins |
| `bootstrappers` | List all discovered bootstrapper names |

## Source Types

### Local repo path

```bash
openbase-coder plugins add ~/code/my-openbase-plugin
```

- Installed editable (`-e`) into the CLI Python environment
- Useful for active plugin development

### GitHub URL

```bash
openbase-coder plugins add https://github.com/org/openbase-plugin
openbase-coder plugins add https://github.com/org/openbase-plugin --ref main
```

- Cloned under `~/.openbase/plugins/sources/`
- Installed pinned to resolved commit SHA

## What Happens on Add/Update/Remove

Mutating plugin commands will:

1. Update plugin registry and requirements under `~/.openbase/plugins/`
2. Sync plugin-declared Claude skills into `${CLAUDE_CONFIG_DIR:-~/.claude}/skills`
3. Regenerate console plugin integration artifacts
4. Restart managed launchd services

Standalone installs support plugin console pages as iframe-backed static assets.
React component console pages still work in dev-workspace mode, where the
workspace console can install plugin npm packages and rebuild from source.

## Plugin Declaration Model

Plugins are Python packages discovered via entry points in:

```toml
[project.entry-points."openbase_coder.plugins"]
my_plugin = "my_plugin.spec:get_plugin_spec"
```

The entry point returns a plugin spec dict containing declarations such as:

- `bootstrappers`
- `stacks`
- `project_views`
- `console_pages`
- `skills`
- `django_url_modules`
- `console_npm_packages`

### Console pages

For install-anywhere plugins, declare iframe console pages with static assets:

```python
{
    "console_pages": [
        {
            "key": "dashboard",
            "title": "Dashboard",
            "asset_dir": "web",
            "entrypoint": "index.html",
        }
    ]
}
```

The CLI copies `asset_dir` into `~/.openbase/plugins/console-assets/` and serves
it under `/openbase-plugin-assets/<plugin>/<page>/`. The console adds the page to
the sidebar from the runtime plugin registry without rebuilding.

Development-mode React component pages can still use `import_module`, `export`,
and `console_npm_packages`, but those pages require a workspace console rebuild
and are rejected by standalone installs.

## Collision Rules

Install/update will fail if a plugin conflicts with existing plugins on:

- bootstrapper name
- console page key
- console page route
- project view stack
