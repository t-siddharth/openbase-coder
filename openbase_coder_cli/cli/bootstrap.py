from __future__ import annotations

import json
from pathlib import Path

import click

from openbase_coder_cli.plugins.manager import run_bootstrapper


def _load_params(params: str, params_file: str) -> dict:
    if params and params_file:
        raise click.ClickException("Use either --params or --params-file, not both")

    if params_file:
        path = Path(params_file).expanduser().resolve()
        if not path.is_file():
            raise click.ClickException(f"Params file not found: {path}")
        payload = json.loads(path.read_text())
    elif params:
        payload = json.loads(params)
    else:
        payload = {}

    if not isinstance(payload, dict):
        raise click.ClickException("Bootstrap params must be a JSON object")

    return payload


@click.command()
@click.argument("bootstrapper_name")
@click.option(
    "--params",
    default="",
    help="JSON object string of bootstrap params.",
)
@click.option(
    "--params-file",
    default="",
    help="Path to JSON file containing bootstrap params.",
)
def bootstrap(bootstrapper_name: str, params: str, params_file: str) -> None:
    """Run a plugin bootstrapper by name."""
    payload = _load_params(params=params, params_file=params_file)
    result = run_bootstrapper(bootstrapper_name, params=payload)
    click.echo(json.dumps(result, indent=2))
