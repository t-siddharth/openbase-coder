# services install

Generate wrappers/plists and bootstrap default launchd services.

## Usage

```bash
openbase-coder services install
```

## What It Does

1. Reads `~/.openbase/installation.json`.
2. Generates shell wrappers in `~/.openbase/launchd/`.
3. Generates plists in `~/Library/LaunchAgents/`.
4. Bootstraps each default service with `launchctl`.
5. Writes logs to `~/.openbase/logs/`.

For workspace-managed services, generated wrappers prefer binaries from
`<workspace>/.venv/bin/`, then `<workspace>/cli/.venv/bin/`, then
`<workspace>/agent/.venv/bin/`
before falling back to `PATH`.
`livekit-server` is still resolved from `PATH` or `/opt/homebrew/bin/livekit-server`.

Optional services, such as `codex-thread-device-sync`, are not installed by
default. Start one explicitly when the local machine is configured for that
workflow:

```bash
openbase-coder services start codex-thread-device-sync
```
