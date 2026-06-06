from __future__ import annotations

import logging
import time
from collections import Counter
from pathlib import Path

import click

from openbase_coder_cli.mcp.thread_import import (
    CodexThreadSyncResult,
    sync_codex_threads_once,
)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(asctime)s %(name)s %(message)s",
    )


def _sync_result_summary(results: list[CodexThreadSyncResult]) -> dict[str, str | int]:
    statuses = Counter(result.status for result in results)
    reasons = Counter(f"{result.status}:{result.reason}" for result in results)
    directions = Counter(result.direction or "none" for result in results)
    return {
        "total": len(results),
        "transferred": statuses["transferred"],
        "conflicts": statuses["conflict"],
        "errors": statuses["error"],
        "skipped": statuses["skipped"],
        "already_synced": statuses["already_synced"],
        "reason_counts": _format_counts(reasons),
        "direction_counts": _format_counts(directions),
    }


def _format_counts(counts: Counter[str]) -> str:
    if not counts:
        return "none"
    return ",".join(f"{key}:{counts[key]}" for key in sorted(counts))


@click.group("codex-sync")
def codex_sync() -> None:
    """Synchronize threads between normal and Openbase Codex homes."""


@codex_sync.command("once")
@click.option("--stability-delay", default=0.2, show_default=True, type=float)
@click.option("--max-age-days", default=15, show_default=True, type=int)
@click.option("--ledger", type=click.Path(path_type=Path), default=None)
@click.option("--verbose", is_flag=True)
def once(
    stability_delay: float,
    max_age_days: int,
    ledger: Path | None,
    verbose: bool,
) -> None:
    """Run one Codex thread sync pass."""
    _configure_logging(verbose)
    kwargs = {
        "stability_delay_seconds": max(stability_delay, 0.0),
        "max_age_days": max(max_age_days, 0),
    }
    if ledger is not None:
        kwargs["ledger_path"] = ledger
    results = sync_codex_threads_once(**kwargs)
    transferred = sum(1 for result in results if result.status == "transferred")
    conflicts = sum(1 for result in results if result.status == "conflict")
    skipped = sum(1 for result in results if result.status == "skipped")
    click.echo(
        f"Codex thread sync complete: transferred={transferred} conflicts={conflicts} skipped={skipped} total={len(results)}"
    )


@codex_sync.command("run")
@click.option("--interval", default=60.0, show_default=True, type=float)
@click.option("--stability-delay", default=0.2, show_default=True, type=float)
@click.option("--max-age-days", default=15, show_default=True, type=int)
@click.option("--ledger", type=click.Path(path_type=Path), default=None)
@click.option("--verbose", is_flag=True)
def run(
    interval: float,
    stability_delay: float,
    max_age_days: int,
    ledger: Path | None,
    verbose: bool,
) -> None:
    """Run Codex thread sync forever on a polling interval."""
    _configure_logging(verbose)
    logger = logging.getLogger(__name__)
    poll_interval = max(interval, 1.0)
    logger.info("codex_thread_sync service_started interval=%s", poll_interval)
    while True:
        started = time.monotonic()
        try:
            kwargs = {
                "stability_delay_seconds": max(stability_delay, 0.0),
                "max_age_days": max(max_age_days, 0),
            }
            if ledger is not None:
                kwargs["ledger_path"] = ledger
            results = sync_codex_threads_once(**kwargs)
            summary = _sync_result_summary(results)
            logger.info(
                "codex_thread_sync sweep_complete total=%s transferred=%s "
                "conflicts=%s errors=%s skipped=%s already_synced=%s "
                "reason_counts=%s direction_counts=%s",
                summary["total"],
                summary["transferred"],
                summary["conflicts"],
                summary["errors"],
                summary["skipped"],
                summary["already_synced"],
                summary["reason_counts"],
                summary["direction_counts"],
            )
        except Exception:
            logger.exception("codex_thread_sync sweep_failed")
        elapsed = time.monotonic() - started
        time.sleep(max(poll_interval - elapsed, 1.0))
