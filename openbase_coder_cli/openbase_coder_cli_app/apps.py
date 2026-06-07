"""
Django app configuration for openbase_coder_cli_app.
"""

from __future__ import annotations

from django.apps import AppConfig


class OpenbaseCoderCliAppConfig(AppConfig):
    """Configuration for the openbase_coder_cli_app Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "openbase_coder_cli.openbase_coder_cli_app"
    verbose_name = "Openbase Coder Cli"

    def ready(self):
        pass
