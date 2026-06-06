import logging
from typing import Any


class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis to log levels."""

    FORMATS = {
        logging.DEBUG: "%(message)s",
        logging.INFO: "%(message)s",
        logging.WARNING: "⚠️  %(message)s",
        logging.ERROR: "❌ %(message)s",
        logging.CRITICAL: "🚨 %(message)s",
    }

    def format(self, record: Any) -> str:
        format_str = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        formatter = logging.Formatter(format_str)
        return formatter.format(record)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure logging with emoji formatting."""
    handler = logging.StreamHandler()
    handler.setFormatter(EmojiFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers
    root_logger.handlers = []
    root_logger.addHandler(handler)
