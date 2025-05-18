"""Tests for the logger module."""

import logging

from gutenberg_downloader.logger import setup_logger


def test_setup_logger_default():
    """Test setup_logger with default parameters."""
    logger = setup_logger("test_logger1")

    assert logger.name == "test_logger1"
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_setup_logger_custom_level():
    """Test setup_logger with custom logging level."""
    logger = setup_logger("test_logger2", level=logging.DEBUG)

    assert logger.name == "test_logger2"
    assert logger.level == logging.DEBUG


def test_setup_logger_custom_format():
    """Test setup_logger with custom format string."""
    custom_format = "%(levelname)s - %(message)s"
    logger = setup_logger("test_logger3", format_string=custom_format)

    handler = logger.handlers[0]
    assert handler.formatter._fmt == custom_format


def test_setup_logger_no_duplicate_handlers():
    """Test that setup_logger doesn't create duplicate handlers."""
    logger_name = "test_logger4"

    # Setup logger twice
    logger1 = setup_logger(logger_name)
    logger2 = setup_logger(logger_name)

    # Should be the same logger instance
    assert logger1 is logger2

    # Should still have only one handler
    assert len(logger2.handlers) == 1


def test_logger_output(caplog):
    """Test that logger outputs messages correctly."""
    logger = setup_logger("test_logger5")

    with caplog.at_level(logging.INFO):
        logger.info("Test info message")
        logger.warning("Test warning message")

    assert "Test info message" in caplog.text
    assert "Test warning message" in caplog.text


def test_logger_level_filtering(caplog):
    """Test that logger filters messages based on level."""
    logger = setup_logger("test_logger6", level=logging.WARNING)

    with caplog.at_level(logging.DEBUG):
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

    # Debug and Info should not appear
    assert "Debug message" not in caplog.text
    assert "Info message" not in caplog.text

    # Warning and Error should appear
    assert "Warning message" in caplog.text
    assert "Error message" in caplog.text
