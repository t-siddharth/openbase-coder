from __future__ import annotations

import subprocess

import click

from openbase_coder_cli.services.boilersync import resolve_boilersync_binary


@click.command(
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
        "help_option_names": [],
    }
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def boilersync(args: tuple[str, ...]) -> None:
    """Pass through to the installed boilersync CLI."""
    boilersync_bin = resolve_boilersync_binary()
    if not boilersync_bin:
        raise click.ClickException("boilersync was not found on PATH.")

    try:
        result = subprocess.run([boilersync_bin, *args])
    except OSError as exc:
        raise click.ClickException(f"Unable to run boilersync: {exc}") from exc

    if result.returncode != 0:
        raise click.exceptions.Exit(result.returncode)
