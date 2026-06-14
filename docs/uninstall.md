# Uninstall Openbase CLI

Uninstall does not depend on the `openbase-coder` command. Use normal macOS,
Linux, and Python tool cleanup commands so you can remove Openbase even if the
CLI environment is broken.

## macOS Launchd Services

Stop and remove the launchd jobs first:

```bash
for plist in "$HOME"/Library/LaunchAgents/com.openbase.coder.*.plist; do
  [ -e "$plist" ] || continue
  launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
done

rm -f "$HOME"/Library/LaunchAgents/com.openbase.coder.*.plist
```

## Linux Systemd User Services

If the machine was set up with systemd user units, stop and remove them first:

```bash
systemctl --user stop 'com.openbase.coder.*.service' 2>/dev/null || true
rm -f "$HOME"/.config/systemd/user/com.openbase.coder.*.service
systemctl --user daemon-reload
```

## Remove The CLI Package

Remove the persistent `openbase-coder` command with the same tool used to
install it:

=== "uv tool"

    ```bash
    uv tool uninstall openbase-coder
    ```

=== "pipx"

    ```bash
    pipx uninstall openbase-coder
    ```

=== "pip"

    ```bash
    pip uninstall openbase-coder
    ```

## Remove Or Archive Local State

Only remove or archive `~/.openbase` after the service jobs above are stopped
and deleted. That directory contains logs, tokens, plugins, generated service
wrappers, the workspace checkout, and the local database.

To remove it completely:

```bash
rm -rf "$HOME"/.openbase
```

To keep a backup instead:

```bash
backup="$HOME/.openbase.backup.$(date +%Y%m%d-%H%M%S)"
mv "$HOME"/.openbase "$backup"
echo "Archived Openbase state at $backup"
```

## Optional Tailscale Cleanup

If this machine only used Tailscale Serve for Openbase, clear the local Serve
configuration after services are removed:

```bash
tailscale serve reset
```
