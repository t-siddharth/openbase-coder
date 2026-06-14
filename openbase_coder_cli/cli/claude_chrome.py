from __future__ import annotations

from pathlib import Path

import click

from openbase_coder_cli.cli.computer_use import (
    CompanionClient,
    _load_companion_session,
)


@click.group("claude-chrome")
def claude_chrome() -> None:
    """Use Claude --chrome while sharing only one Chrome window."""


@claude_chrome.command("start")
@click.argument("instructions", nargs=-1, required=True)
@click.option("--room", "room_name", default="", help="Explicit LiveKit room name.")
@click.option(
    "--url",
    "target_url",
    default="about:blank",
    show_default=True,
    help="Initial Chrome URL to share.",
)
@click.option(
    "--command",
    default="claude",
    show_default=True,
    help="Claude executable or command name.",
)
@click.option(
    "--cwd",
    default=".",
    show_default=True,
    help="Working directory for the Claude command.",
)
@click.option(
    "--max-turns", type=int, default=None, help="Optional Claude --max-turns value."
)
@click.option(
    "--permission-mode",
    type=click.Choice(
        ["acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan"]
    ),
    default="default",
    show_default=True,
)
@click.option(
    "--allowed-tool",
    "allowed_tools",
    multiple=True,
    help="Allowed Claude tool. Can be repeated.",
)
@click.option(
    "--chrome-profile-directory",
    default="",
    help="Chrome profile directory when using the default user data dir.",
)
@click.option(
    "--isolated-profile",
    is_flag=True,
    help="Use a temporary Chrome profile instead of the default Chrome profile.",
)
@click.option(
    "--no-launch",
    is_flag=True,
    help="Do not launch the companion app if its IPC server is not reachable.",
)
def start(
    instructions: tuple[str, ...],
    room_name: str,
    target_url: str,
    command: str,
    cwd: str,
    max_turns: int | None,
    permission_mode: str,
    allowed_tools: tuple[str, ...],
    chrome_profile_directory: str,
    isolated_profile: bool,
    no_launch: bool,
) -> None:
    """Share one Chrome window and run Claude Code with --chrome."""
    text = " ".join(instructions).strip()
    if not text:
        raise click.ClickException("Claude Chrome instructions are required.")
    if max_turns is not None and max_turns < 1:
        raise click.ClickException("--max-turns must be at least 1.")

    client = CompanionClient()
    if not no_launch:
        client.ensure_running()

    status_payload = client.status()
    if status_payload.get("state") in {
        "controlling",
        "starting-control",
        "chrome-controlling",
        "starting-chrome-control",
    }:
        raise click.ClickException("A control run is already active.")

    session = _load_companion_session(room_name)
    response = client.start_claude_chrome(
        session=session,
        instructions=text,
        target_url=target_url.strip() or "about:blank",
        command=command.strip() or None,
        cwd=str(Path(cwd).expanduser().resolve()) if cwd.strip() else None,
        max_turns=max_turns,
        permission_mode=permission_mode.strip() or None,
        allowed_tools=[tool for tool in allowed_tools if tool.strip()],
        chrome_profile_directory=chrome_profile_directory.strip() or None,
        chrome_use_default_profile=not isolated_profile,
    )
    click.echo(
        f"Claude Chrome control started ({response.get('state') or 'chrome-controlling'}). "
        "Only the Chrome window is shared."
    )


@claude_chrome.command("steer")
@click.argument("instructions", nargs=-1, required=True)
def steer(instructions: tuple[str, ...]) -> None:
    """Replace the active Claude --chrome command with a continued steering prompt."""
    text = " ".join(instructions).strip()
    if not text:
        raise click.ClickException("Steering instructions are required.")

    response = CompanionClient().steer_claude_chrome(text)
    click.echo(
        f"Claude Chrome steering submitted ({response.get('state') or 'chrome-controlling'})."
    )


@claude_chrome.command("queue")
@click.argument("instructions", nargs=-1, required=True)
def queue(instructions: tuple[str, ...]) -> None:
    """Queue a continued Claude --chrome prompt after the active one exits."""
    text = " ".join(instructions).strip()
    if not text:
        raise click.ClickException("Queued Claude Chrome instructions are required.")

    response = CompanionClient().queue_claude_chrome(text)
    click.echo(
        f"Claude Chrome instruction queued ({response.get('state') or 'chrome-controlling'})."
    )


@claude_chrome.command("abort")
def abort() -> None:
    """Abort Claude --chrome and stop the shared Chrome window."""
    response = CompanionClient().abort_claude_chrome()
    click.echo(f"Claude Chrome control aborted ({response.get('state') or 'off'}).")


@claude_chrome.command("status")
def status() -> None:
    """Show the companion control status."""
    response = CompanionClient().status()
    state = response.get("state") or "unknown"
    click.echo(f"Companion state: {state}")
    if error := response.get("error"):
        click.echo(f"Error: {error}")
