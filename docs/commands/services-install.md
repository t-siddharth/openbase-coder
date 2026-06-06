# services install

Generate wrappers/plists and bootstrap all launchd services.

## Usage

```bash
openbase-coder services install
```

## What It Does

1. Reads `~/.openbase/installation.json`.
2. Generates shell wrappers in `~/.openbase/launchd/`.
3. Generates plists in `~/Library/LaunchAgents/`.
4. Bootstraps each service with `launchctl`.
5. Writes logs to `~/.openbase/logs/`.

For workspace-managed services, generated wrappers prefer binaries from
`<workspace>/.venv/bin/`, then `<workspace>/cli/.venv/bin/`, then
`<workspace>/agent/.venv/bin/`
before falling back to `PATH`.
`livekit-server` is still resolved from `PATH` or `/opt/homebrew/bin/livekit-server`.
