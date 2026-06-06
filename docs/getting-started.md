# Getting Started

This guide sets up Openbase locally using the `openbase-coder` CLI.

## Prerequisites

- macOS (required for `setup` and `services`, which use launchd)
- Python 3.13+
- Git
- `uv` (recommended)
- `npm` (for console build during setup)
- `livekit-server` on your `PATH` (for voice services)

Optional but recommended:

- `multi` on your `PATH` for automatic workspace sub-repo sync

## Install

=== "pipx"

    ```bash
    pipx install openbase-coder
    ```

=== "uv"

    ```bash
    uv tool install openbase-coder
    ```

=== "pip"

    ```bash
    pip install openbase-coder
    ```

Verify:

```bash
openbase-coder --version
```

## First-Time Setup

Run:

```bash
openbase-coder setup
```

What setup does:

1. Clones or updates the Openbase workspace at `~/.openbase/workspace`.
2. Writes `~/.openbase/installation.json`.
3. Generates `~/.openbase/.env` (if it does not already exist).
4. Creates missing default instruction files in `~/.openbase/codex_home` from the workspace `instructions/` directory.
5. Symlinks workspace skills into `~/.openbase/codex_home/skills`.
6. Initializes the CLI workspace and bundled LiveKit worker (`uv sync`, LiveKit model downloads).
7. Writes Codex app-server defaults such as `CODEX_MODEL=gpt-5.5`, `CODEX_MODEL_REASONING_EFFORT=high`, `CODEX_SERVICE_TIER=fast`, `CODEX_APP_SERVER_URL`, and `LIVEKIT_CODEX_THREAD_CWD`.
8. Builds `console`.
9. Installs launchd services (unless `--skip-services`).

## Start the Server

```bash
openbase-coder server --host 0.0.0.0 --port 7999
```

By default this command:

- Runs Django migrations
- Runs `collectstatic`
- Rebuilds the console
- Starts Gunicorn + Uvicorn worker(s)

## Health Check

```bash
openbase-coder doctor
openbase-coder services status
```

## Authenticate With Openbase Cloud (Optional)

```bash
openbase-coder login --email you@example.com
```

This stores tokens in `~/.openbase/auth.json` for JWT-based auth flows.

## Next Steps

- Learn command details in [Commands](commands/index.md)
- Install your first plugin: `openbase-coder plugins add <local-repo-or-github-url>`
- Discover bootstrap commands: `openbase-coder plugins bootstrappers`
- Run plugin bootstrap flow: `openbase-coder bootstrap <name> --params-file <file.json>`
- Review environment and auth settings in [Configuration](configuration.md)
- See all runtime artifacts in [Files and Paths](files-and-paths.md)
- Map backend behavior to the iOS UI in [iOS App Tabs](ios-tabs.md)
