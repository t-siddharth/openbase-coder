# claude

Manage Claude Code auth for Openbase's managed `CLAUDE_CONFIG_DIR`.

## Usage

```bash
openbase-coder claude status
openbase-coder claude login
openbase-coder claude sync-state
```

`status` and `login` run Claude Code with
`CLAUDE_CONFIG_DIR=~/.openbase/claude_config`. This is separate from a normal
Claude Code login because Claude Code stores usable OAuth credentials in a
config-dir-scoped credential store.

`sync-state` copies normal Claude Code state from `~/.claude.json` into
`~/.openbase/claude_config.json` while preserving Openbase MCP entries. It does
not log Claude Code in; run `openbase-coder claude login` for that.
