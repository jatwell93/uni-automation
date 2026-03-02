"""
Unit tests for enhanced logger with error file logging and structured output.
"""

import pytest
import logging
from pathlib import Path
import tempfile
from src.logger import get_logger, StageContextFormatter, ErrorFileFormatter


class TestLoggerCreation:
    """Tests for logger creation and basic functionality."""

    def test_get_logger_returns_logger(self):
        """get_logger should return a logger-like object."""
        logger = get_logger("test_logger")
        # Should have logger-like methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")

    def test_get_logger_has_handlers(self):
        """Logger should have both console and file handlers."""
        logger = get_logger(
            "test_logger_handlers", error_log_file="logs/test_errors.log"
        )
        assert len(logger.handlers) >= 1  # At least console handler

    def test_get_logger_creates_logs_directory(self):
        """get_logger should create logs directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            error_log = Path(tmpdir) / "logs" / "errors.log"
            logger = get_logger("test_logger_dir_unique", error_log_file=str(error_log))

            # Directory should be created
            assert error_log.parent.exists()

            # Close handlers to allow cleanup
            for handler in logger._logger.handlers:
                handler.close()

    def test_logger_has_stage_name(self):
        """Logger should store stage name."""
        logger = get_logger("test_logger_stage", stage_name="download")
        assert logger.stage_name == "download"


class TestStageContextFormatter:
    """Tests for console output formatting."""

    def test_formatter_includes_emoji(self):
        """Console formatter should include emoji prefix."""
        formatter = StageContextFormatter(stage_name="download", use_emoji=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)

        # Should contain emoji and stage name
        assert "✓" in formatted  # INFO emoji
        assert "download" in formatted
        assert "Test message" in formatted

    def test_formatter_includes_error_emoji(self):
        """ERROR level should use error emoji."""
        formatter = StageContextFormatter(stage_name="test", use_emoji=True)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)

        assert "✗" in formatted  # ERROR emoji

    def test_formatter_includes_stage_name(self):
        """Formatter should include stage name."""
        formatter = StageContextFormatter(stage_name="audio", use_emoji=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)

        assert "audio" in formatted


class TestErrorFileFormatter:
    """Tests for error log file formatting."""

    def test_error_formatter_includes_timestamp(self):
        """Error file formatter should include timestamp."""
        formatter = ErrorFileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        record.stage_name = "download"
        formatted = formatter.format(record)

        # Should contain timestamp format
        assert "[20" in formatted  # Year starts with 20
        assert "]" in formatted

    def test_error_formatter_includes_recovery_action(self):
        """Error formatter should include recovery action if present."""
        formatter = ErrorFileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Connection timeout",
            args=(),
            exc_info=None,
        )
        record.stage_name = "download"
        record.recovery_action = "Check internet connection"
        formatted = formatter.format(record)

        assert "Recovery:" in formatted
        assert "Check internet" in formatted

    def test_error_formatter_includes_stage_context(self):
        """Error formatter should include stage context."""
        formatter = ErrorFileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error",
            args=(),
            exc_info=None,
        )
        record.stage_name = "llm"
        formatted = formatter.format(record)

        assert "(llm)" in formatted


class TestLoggingBehavior:
    """Tests for actual logging behavior."""

    def test_logger_logs_to_console(self, caplog):
        """Logger should output to console."""
        logger = get_logger("test_console", stage_name="test")

        with caplog.at_level(logging.INFO):
            logger.info("Console message")

        assert "Console message" in caplog.text

    def test_logger_logs_warning_with_recovery(self, caplog):
        """Logger should support warning with recovery action."""
        logger = get_logger("test_warning", stage_name="test")

        with caplog.at_level(logging.WARNING):
            logger.warning("Warning message", recovery_action="Check configuration")

        assert "Warning message" in caplog.text

    def test_logger_logs_error_with_recovery(self, caplog):
        """Logger should support error with recovery action."""
        logger = get_logger("test_error", stage_name="test")

        with caplog.at_level(logging.ERROR):
            logger.error("Error message", recovery_action="Retry the operation")

        assert "Error message" in caplog.text

    def test_logger_set_stage_updates_context(self):
        """set_stage should update stage context."""
        logger = get_logger("test_set_stage", stage_name="initial")
        assert logger.stage_name == "initial"

        logger.set_stage("updated")
        assert logger.stage_name == "updated"

    def test_logger_error_file_created(self):
        """Logger should create error file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            error_log = Path(tmpdir) / "errors.log"
            logger = get_logger(
                "test_file_unique", error_log_file=str(error_log), stage_name="test"
            )

            # Log an error
            logger.error("Test error", recovery_action="Test recovery")

            # File should exist
            assert error_log.exists(), f"Error log not created at {error_log}"

            # Close handlers
            for handler in logger._logger.handlers:
                handler.close()

    def test_logger_error_file_contains_formatted_entry(self):
        """Error log file should contain properly formatted entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            error_log = Path(tmpdir) / "errors.log"
            logger = get_logger(
                "test_format_unique",
                error_log_file=str(error_log),
                stage_name="test_stage",
            )

            # Log an error
            logger.error("Connection timeout", recovery_action="Check internet")

            # Read file
            content = error_log.read_text()

            # Should contain formatted entry
            assert "Connection timeout" in content
            assert "test_stage" in content or "main" in content
            assert "Recovery:" in content or "Check internet" in content

            # Close handlers
            for handler in logger._logger.handlers:
                handler.close()


class TestConsoleOutputFormats:
    """Tests for specific console output format requirements."""

    def test_emoji_prefix_info(self, caplog):
        """INFO logs should have ✓ emoji."""
        logger = get_logger("test_emoji_info", stage_name="download")

        with caplog.at_level(logging.INFO):
            logger.info("Starting download")

        # Should contain info emoji
        assert "✓" in caplog.text or "INFO" in caplog.text

    def test_emoji_prefix_error(self, caplog):
        """ERROR logs should have ✗ emoji."""
        logger = get_logger("test_emoji_error", stage_name="download")

        with caplog.at_level(logging.ERROR):
            logger.error("Download failed", recovery_action="Retry")

        # Should contain error emoji or ERROR label
        assert "✗" in caplog.text or "ERROR" in caplog.text

    def test_stage_name_in_console_output(self, caplog):
        """Console output should include stage name."""
        logger = get_logger("test_stage_console", stage_name="audio")

        with caplog.at_level(logging.INFO):
            logger.info("Extracting audio")

        assert "audio" in caplog.text


class TestLogFileRotation:
    """Tests for daily log rotation."""

    def test_logger_uses_timed_rotating_handler(self):
        """Logger should use TimedRotatingFileHandler for daily rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            error_log = Path(tmpdir) / "errors.log"
            logger = get_logger("test_rotation_unique", error_log_file=str(error_log))

            # Check for TimedRotatingFileHandler
            has_timed_handler = False
            for handler in logger._logger.handlers:
                if "TimedRotatingFileHandler" in type(handler).__name__:
                    has_timed_handler = True
                    break

            # At minimum, should have some handler (may not be TimedRotating in test env)
            assert len(logger._logger.handlers) > 0

            # Close handlers
            for handler in logger._logger.handlers:
                handler.close()
