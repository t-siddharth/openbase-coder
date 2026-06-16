# Openbase Coder

Openbase Coder is a local voice-coding runtime for working with AI coding
agents from your Mac, browser, and Openbase clients.

The `openbase-coder` command installs and runs the local services that power
Openbase Coder: a Django API, WebSocket endpoints, Codex/Super Agents
coordination, local project and diff APIs, LiveKit voice services, plugin
management, and the bundled web console.

This repository is the main open-source entrypoint for the Openbase Coder
runtime.

## What It Provides

- Local API and WebSocket server for coding sessions, diffs, approvals, reports,
  project metadata, and service status
- Local per-machine thread favorite metadata exposed on thread list/detail APIs
- Voice-agent runtime built around LiveKit and Codex app-server sessions
- One-command macOS/Linux setup for the Openbase workspace, environment file,
  console build, background services, and default agent instructions
- Plugin installation and bootstrap commands for extending the local runtime
- Openbase Cloud login support for authenticated client workflows
- A local web console served by the CLI

## Requirements

- macOS (launchd) or Linux (systemd user services) for setup and service
  management; screen sharing and computer use are macOS-only
- Python 3.13+
- Git
- `uv` for the recommended install/setup flow and local development
- Node package tooling for the bundled console build
- `livekit-server` on `PATH` for voice services

## Quick Start

Recommended one-line setup with `uvx`:

```bash
uvx --python 3.13 openbase-coder setup
```

This runs the latest published `openbase-coder` package in an isolated `uv`
tool environment and starts the normal first-time setup flow.

For a persistent command on your `PATH` after setup, install with `uv tool`:

```bash
uv tool install --python 3.13 openbase-coder
openbase-coder setup
```

`pipx` is also supported when you already manage Python tools that way:

```bash
pipx install --python python3.13 openbase-coder
```

Verify a persistent install:

```bash
openbase-coder --version
```

## First-Time Setup

If you already installed the persistent `openbase-coder` command, run:

```bash
openbase-coder setup
```

Setup clones the public Openbase Coder workspace into `~/.openbase/workspace`,
syncs the runtime install set, generates `~/.openbase/.env` if needed, builds
the web console, installs launchd services, and prepares the local Codex home
used by voice sessions.

After setup, check the local runtime:

```bash
uvx --python 3.13 openbase-coder doctor
uvx --python 3.13 openbase-coder services status
```

## Run The Server

For foreground development:

```bash
uvx --python 3.13 openbase-coder server --host 0.0.0.0 --port 7999
```

For normal macOS background operation:

```bash
uvx --python 3.13 openbase-coder services start
uvx --python 3.13 openbase-coder services status
```

## Common Commands

```bash
uvx --python 3.13 openbase-coder setup
uvx --python 3.13 openbase-coder doctor
uvx --python 3.13 openbase-coder login
uvx --python 3.13 openbase-coder services status
uvx --python 3.13 openbase-coder services logs django-cli
uvx --python 3.13 openbase-coder plugins list
uvx --python 3.13 openbase-coder bootstrap --help
```

If you installed with `uv tool`, omit `uvx --python 3.13` from those commands.

## Documentation

- [Getting Started](docs/getting-started.md)
- [Commands](docs/commands/index.md)
- [Configuration](docs/configuration.md)
- [Files and Paths](docs/files-and-paths.md)
- [iOS App](docs/ios-tabs.md)
- [Troubleshooting](docs/troubleshooting.md)

## Development

From this repository:

```bash
uv sync --extra dev
uv run openbase-coder --version
uv run pytest
```

The CLI is part of the larger Openbase Coder multi-workspace. The public setup
flow only syncs the runtime install set required by end users.

## License

Openbase Coder CLI is licensed under
[AGPL-3.0-only](LICENSE).
