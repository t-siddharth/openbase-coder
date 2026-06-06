# services stop

Stop all services or one named service.

## Usage

```bash
openbase-coder services stop [NAME]
```

This performs `launchctl bootout` and keeps jobs unloaded until restarted.

## Example

```bash
openbase-coder services stop codex-app-server
```
