import functools
import logging
import sys
import traceback

import click

from openbase_coder_cli.logging import configure_logging


def common_command_wrapper(command_to_wrap: click.Command) -> click.Command:
    """
    Wraps an existing Click command to add common functionality:
    - A --verbose option for detailed logging.
    - Standardized error handling and logging.
    This function modifies the command_to_wrap in-place.
    """
    original_callback = command_to_wrap.callback
    if not original_callback:
        # This should generally not happen if command_to_wrap is created via @click.command
        raise ValueError(
            f"Command '{command_to_wrap.name or 'Unnamed'}' has no callback to wrap."
        )

    @functools.wraps(original_callback)
    def new_wrapped_callback(**kwargs):
        # Pop the verbose flag. It's added by this wrapper to the command's params.
        # Click will pass it in kwargs to this new_callback.
        verbose_value = kwargs.pop("verbose", False)

        # Configure logging based on verbosity
        log_level = logging.DEBUG if verbose_value else logging.INFO
        configure_logging(level=log_level)

        exit_code = None
        try:
            # Call the original command's callback with its intended kwargs
            return original_callback(**kwargs)
        except Exception as e:
            logger = logging.getLogger(__name__)  # Get logger after configuration
            logger.error(str(e))  # This will use the emoji formatter
            if verbose_value:
                # For verbose mode, also print traceback directly to stderr
                click.secho("\nDebug traceback:", fg="yellow", err=True)
                click.secho(traceback.format_exc(), fg="yellow", err=True)
            exit_code = 1

        if exit_code is not None:
            sys.exit(exit_code)

    # Replace the command's callback with our new wrapped version
    command_to_wrap.callback = new_wrapped_callback

    # Add the --verbose option to the command's parameters, if not already present
    # This ensures the `verbose` kwarg is available in new_wrapped_callback
    if not any(
        isinstance(p, click.Option) and p.name == "verbose"
        for p in command_to_wrap.params
    ):
        verbose_option = click.Option(
            ["--verbose"],
            is_flag=True,
            help="Enable verbose output.",
            # expose_value=True is default, making 'verbose' a kwarg to the callback
        )
        command_to_wrap.params.append(verbose_option)

    return command_to_wrap  # Return the modified command
