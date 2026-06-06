# services uninstall

Unload and remove all managed launchd services.

## Usage

```bash
openbase-coder services uninstall
```

Removes:

- `~/Library/LaunchAgents/com.openbase.coder.*.plist`
- `~/.openbase/launchd/*.sh`

Log files are preserved in `~/.openbase/logs/`.
