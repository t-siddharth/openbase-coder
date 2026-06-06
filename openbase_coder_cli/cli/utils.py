"""
CLI utility functions for openbase_coder_cli.

This module provides utilities for setting up the Django environment,
running migrations, and managing secrets.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path


def get_data_dir() -> Path:
    """Get the data directory for storing persistent data."""
    from openbase_coder_cli.paths import OPENBASE_BASE_DIR

    data_dir = Path(os.environ.get("OPENBASE_CODER_CLI_DATA_DIR", OPENBASE_BASE_DIR))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_env_file() -> Path:
    """Get the path to the .env file."""
    from openbase_coder_cli.services.installation import InstallationConfig

    if InstallationConfig.exists():
        config = InstallationConfig.load()
        return Path(config.env_file)
    return get_data_dir() / ".env"


def generate_secret_key() -> str:
    """Generate a secure secret key for Django."""
    return secrets.token_urlsafe(50)


def generate_api_token() -> str:
    """Generate a secure API token."""
    return secrets.token_urlsafe(32)


def setup_django_environment() -> dict[str, str]:
    """
    Set up the Django environment.

    This function:
    1. Ensures the .env file exists with required secrets
    2. Loads environment variables
    3. Sets the Django settings module

    Returns the environment variables dict.
    """
    env_vars = os.environ

    # Set environment variables
    for key, value in env_vars.items():
        os.environ.setdefault(key, value)

    # Set Django settings module
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "openbase_coder_cli.config.settings"
    )

    return env_vars


def run_migrations() -> None:
    """Run Django migrations."""
    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", verbosity=1)


def run_collectstatic() -> None:
    """Run Django collectstatic."""
    import django
    from django.core.management import call_command

    django.setup()
    call_command("collectstatic", verbosity=0, interactive=False)
