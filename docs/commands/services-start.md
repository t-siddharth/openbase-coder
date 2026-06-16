# services start

Start default services or one named service.

## Usage

```bash
openbase-coder services start [NAME]
```

## Examples

```bash
# Start default services
openbase-coder services start

# Start only Django API
openbase-coder services start django-cli

# Opt into cross-device Codex thread snapshot sync
openbase-coder services start codex-thread-device-sync
```
