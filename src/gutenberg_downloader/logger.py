"""Centralized logging configuration for Gutenberg Downloader."""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "gutenberg_downloader",
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Set up and configure a logger instance.

    Args:
        name: Logger name. Defaults to "gutenberg_downloader".
        level: Logging level. Defaults to INFO.
        format_string: Custom format string. Defaults to a standard format.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Set logger level
    logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


# Create default logger instance
logger = setup_logger()
