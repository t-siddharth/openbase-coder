# services logs

Tail stdout/stderr logs for one service.

## Usage

```bash
openbase-coder services logs NAME
```

## Example

```bash
openbase-coder services logs django-cli
```

Log files live at `~/.openbase/logs/<service>.stdout.log` and `.stderr.log`.
