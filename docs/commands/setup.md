# setup

Run the full Openbase local installation flow.

## Usage

```bash
openbase-coder setup [OPTIONS]
```

## Backend Selection

Setup can choose the default coding backend:

```bash
openbase-coder setup --backend codex
openbase-coder setup --backend claude-agent-sdk
openbase-coder setup --backend claude-tui
```

New env files default to `codex` when `--backend` is omitted.
Existing env files are left unchanged unless `--backend` is passed.

- `codex`: default native Codex app-server with OpenAI models.
- `claude-agent-sdk`: Claude Agent SDK backend. It uses the Claude Agent SDK
  directly for Super Agents UI-driver sessions and uses local Claude
  auth/billing instead of `ANTHROPIC_API_KEY`.
- `claude-tui`: uses the local Claude Code CLI/TUI login directly, does not
  require an Anthropic API key, and is used by Super Agents UI-driver sessions.

For first-time setup without installing the CLI first, prefer `uvx`:

```bash
uvx --python 3.13 openbase-coder setup
```

## Options

| Option | Default | Description |
|---|---|---|
| `--workspace-dir PATH` | `~/.openbase/workspace` | Workspace clone location |
| `--env-file PATH` | `~/.openbase/.env` | Shared environment file path |
| `--assembly-ai-api-key TEXT` | env `ASSEMBLY_AI_API_KEY` | Optional STT key |
| `--cartesia-api-key TEXT` | env `CARTESIA_API_KEY` | Optional TTS key |
| `--skip-clone` | `false` | Skip workspace clone/pull |
| `--skip-services` | `false` | Skip service install |
| `--link-codex-config` | `false` | Symlink Openbase's service Codex config to `~/.codex/config.toml` |

## Behavior Details

`setup` runs on macOS (launchd) and Linux (systemd user services) and performs these phases:

1. Ensures `~/.openbase` exists.
2. Clones/pulls `openbase-coder-workspace`.
3. Runs `multi sync` if `multi` is available.
4. Writes `installation.json` with `workspace_path` and `env_file`.
5. Creates `.env` with generated secrets if missing.
6. Symlinks `~/.openbase/codex_home/auth.json` to `~/.codex/auth.json` so launchd Codex services use the normal Codex login.
7. Maintains `~/.openbase/codex_home/AGENTS.md` and `~/.openbase/claude_config/CLAUDE.md` as editable files with a refreshed `## Openbase Coder Instructions` section generated from the workspace `instructions/AGENTS.md`.
8. Symlinks shared default instruction files from `instructions/` into `~/.openbase/instructions/`, and keeps legacy Codex-home instruction symlinks pointed there.
9. Creates missing `~/.openbase/dispatcher-config.json` with dispatcher reasoning effort `low`, Super Agents reasoning effort `high`, and backend-specific model defaults, and keeps `~/.openbase/codex_home/dispatcher-config.json` as a legacy symlink.
10. Symlinks workspace skills from `skills/skills/` into `~/.openbase/codex_home/skills` and `~/.openbase/claude_config/skills`.
11. Initializes `cli` with `uv sync` and LiveKit model downloads.
12. Configures `~/.openbase/codex_home/config.toml` with full Codex local access (`sandbox_mode = "danger-full-access"`), disabled permission prompts, and the Super Agents MCP server. With `--link-codex-config`, this path is first linked to `~/.codex/config.toml`. The MCP command prefers the selected workspace's venv executable and falls back to the resolved local `uv` path.
13. Configures `~/.openbase/claude_config/.claude.json` with the Super Agents MCP server and writes `CLAUDE_CONFIG_DIR=~/.openbase/claude_config` into the shared `.env`.
14. Writes Codex app-server defaults like `CODEX_MODEL=gpt-5.5`, `CODEX_MODEL_REASONING_EFFORT=high`, `CODEX_SERVICE_TIER=fast`, `CODEX_APP_SERVER_URL`, and `LIVEKIT_CODEX_THREAD_CWD` into the shared `.env`.
15. Builds `console`.
16. Installs background services (launchd on macOS, systemd user units on Linux) unless skipped.
17. Configures Tailscale Serve routes for the iOS app:
    - `tailscale serve --bg --http=18080 http://127.0.0.1:7999`
    - `tailscale serve --bg --tcp=7880 tcp://127.0.0.1:7880`

The generated env file records the selected backend as `OPENBASE_CODING_BACKEND`.
Older env files that still set `OPENBASE_CODEX_BACKEND` are supported as a
fallback.

## Example

```bash
uvx --python 3.13 openbase-coder setup \
  --workspace-dir ~/.openbase/workspace \
  --env-file ~/.openbase/.env
```

## Notes

- If `.env` already exists, setup leaves it unchanged.
- `~/.openbase/codex_home/AGENTS.md` and `~/.openbase/claude_config/CLAUDE.md` remain normal editable files. Setup refreshes only their `## Openbase Coder Instructions` sections from the workspace `instructions/AGENTS.md`; custom content above that section or under a separate H2 is preserved. Shared default instruction files are symlinked under `~/.openbase/instructions`, with legacy Codex-home symlinks kept for compatibility. Existing matching copies are replaced with symlinks; existing customized files are left unchanged.
- If `dispatcher-config.json` already exists, setup preserves it. Legacy configs from `~/.openbase/codex_home/dispatcher-config.json` are migrated to `~/.openbase/dispatcher-config.json`.
- Existing skill symlinks in `~/.openbase/codex_home/skills` and `~/.openbase/claude_config/skills` are updated to the workspace source. Real skill directories or files are left unchanged.
- Existing `~/.openbase/codex_home/config.toml` content is preserved, except setup enforces the root permission keys and creates or replaces the `[mcp_servers.super-agents]` table. Passing `--link-codex-config` makes `~/.openbase/codex_home/config.toml` a symlink to `~/.codex/config.toml`; if the normal Codex config is missing, setup seeds it from the existing Openbase config before linking.
- If `npm`, `uv`, or `multi` are missing, related steps are skipped with messages.
- If Tailscale is missing or disconnected, setup prints the manual Serve
  commands and continues. `openbase-coder doctor` and `openbase-coder services
  status` fail until the Tailscale Serve routes and external Openbase health
  check pass.
