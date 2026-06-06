from __future__ import annotations

import subprocess

import click

from openbase_coder_cli.paths import DEFAULT_LOG_DIR
from openbase_coder_cli.services.definitions import SERVICES, ServiceDefinition
from openbase_coder_cli.services.launchd import (
    install_all_services,
    install_service,
    launchctl_bootout,
    launchctl_status,
    regenerate_all_services,
    uninstall_all_services,
)
from openbase_coder_cli.services.registry import (
    find_service,
    require_installation,
    target_services,
)
from openbase_coder_cli.services.voice_warning import (
    any_service_action_interrupts_voice,
    warn_before_voice_interruption,
)


def _ensure_started(config, svc: ServiceDefinition, verb: str) -> None:
    try:
        install_service(config, svc)
        click.echo(f"  Installed and {verb} {svc.name}")
    except click.ClickException as exc:
        click.echo(f"  Failed to {verb} {svc.name}: {exc}")


@click.group()
def services() -> None:
    """Service lifecycle management for Openbase Coder."""


@services.command()
def install() -> None:
    """Generate and load all launchd services."""
    config = require_installation()
    click.echo("Installing launchd services...")
    install_all_services(config)


@services.command()
@click.argument("name", required=False)
def start(name: str | None) -> None:
    """Start all or one service."""
    config = require_installation()
    for svc in target_services(name):
        _ensure_started(config, svc, "started")


@services.command()
@click.argument("name", required=False)
def stop(name: str | None) -> None:
    """Stop all or one service and keep it stopped (unload launchd job)."""
    require_installation()
    targets = target_services(name)
    if any_service_action_interrupts_voice(targets, "stop"):
        warn_before_voice_interruption(reason="services stop")
    for svc in targets:
        if launchctl_bootout(svc):
            click.echo(f"  Stopped {svc.name}")
        else:
            click.echo(f"  {svc.name} not loaded")


@services.command()
def status() -> None:
    """Show status of all services."""
    require_installation()
    click.echo("Service Status:")
    click.echo()
    for svc in SERVICES:
        info = launchctl_status(svc)
        name_col = f"  {svc.name:<20}"
        if not info["installed"]:
            click.echo(f"{name_col} not installed")
        elif info["pid"]:
            click.echo(f"{name_col} running (pid {info['pid']})")
        else:
            exit_code = info.get("last_exit_code", "unknown")
            click.echo(f"{name_col} loaded (not running, last exit: {exit_code})")
    click.echo()


@services.command()
def uninstall() -> None:
    """Remove all launchd services."""
    require_installation()
    click.echo("Uninstalling launchd services...")
    uninstall_all_services()


@services.command()
@click.argument("name")
def logs(name: str) -> None:
    """Tail logs for a service."""
    require_installation()
    svc = find_service(name)
    combined_log = DEFAULT_LOG_DIR / f"{svc.name}.log"
    legacy_stdout_log = DEFAULT_LOG_DIR / f"{svc.name}.stdout.log"
    legacy_stderr_log = DEFAULT_LOG_DIR / f"{svc.name}.stderr.log"

    if not any(
        path.exists()
        for path in (combined_log, legacy_stdout_log, legacy_stderr_log)
    ):
        raise click.ClickException(f"No log files found for {svc.name}")

    click.echo(f"Tailing logs for {svc.name}... (Ctrl+C to stop)")
    click.echo()

    files = [
        str(f)
        for f in [combined_log, legacy_stdout_log, legacy_stderr_log]
        if f.exists()
    ]
    subprocess.run(["tail", "-f", *files])


@services.command()
def regenerate() -> None:
    """Re-read installation.json, regenerate all plists/wrappers."""
    config = require_installation()
    click.echo("Regenerating wrappers and plists...")
    regenerate_all_services(config)
