from __future__ import annotations

import json

import click


@click.command("super-agent-name")
@click.argument("thread_name")
@click.option("--json", "json_output", is_flag=True, help="Print structured JSON.")
def super_agent_name(thread_name: str, json_output: bool) -> None:
    """Derive the deterministic Super Agent name for a thread name."""
    normalized_thread_name = " ".join(thread_name.split())
    if not normalized_thread_name:
        raise click.ClickException("Thread name is required.")

    from openbase_coder_cli.livekit_voice_route import super_agent_voice_for_context

    voice = super_agent_voice_for_context(
        normalized_thread_name, normalized_thread_name
    )
    if voice is None:
        raise click.ClickException("No Super Agent voice is configured.")

    if json_output:
        click.echo(
            json.dumps(
                {
                    "thread_name": normalized_thread_name,
                    "agent_name": voice.name,
                    "voice_id": voice.voice_id,
                    "voice_name": voice.name,
                },
                sort_keys=True,
            )
        )
        return

    click.echo(voice.name)
