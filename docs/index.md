# Openbase CLI

The Openbase CLI (`openbase-coder`) runs your local Openbase runtime on macOS.

It provides:

- A local Django API + WebSocket server for Codex threads, turns, and diffs
- One-command setup for workspace clone, `.env` generation, and service install
- Launchd service lifecycle management (`openbase-coder services ...`)
- Plugin lifecycle + bootstrap execution (`openbase-coder plugins ...`, `openbase-coder bootstrap ...`)
- Authentication flows for local token auth and Openbase JWT auth
- A backend used directly by the Openbase iOS app

## Quick Start

```bash
# Install (pick one)
pipx install openbase-coder
# or
uv tool install openbase-coder

# Bootstrap Openbase locally (macOS)
openbase-coder setup

# Run server in foreground
openbase-coder server --host 0.0.0.0 --port 7999
```

## Documentation

- [Getting Started](getting-started.md)
- [Commands](commands/index.md)
- [Configuration](configuration.md)
- [Files and Paths](files-and-paths.md)
- [iOS App Tabs](ios-tabs.md)
- [Troubleshooting](troubleshooting.md)
