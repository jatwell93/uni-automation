"""
Enhanced logging module with console and error file output.

Provides dual-channel logging:
- Console: Emoji prefixes, stage name, INFO/DEBUG level
- Error file: Timestamps, stage context, recovery instructions for ERROR/WARNING

Auto-rotates daily error log files.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional


# Color and emoji constants for console output
_LEVEL_EMOJI = {
    "DEBUG": "🔍",
    "INFO": "✓",
    "WARNING": "⚠",
    "ERROR": "✗",
}


class StageContextFormatter(logging.Formatter):
    """Formatter that includes stage context and emoji prefixes."""

    def __init__(self, stage_name: str = "main", use_emoji: bool = True):
        super().__init__()
        self.stage_name = stage_name
        self.use_emoji = use_emoji

    def format(self, record):
        # Console format: emoji | stage: message
        emoji = _LEVEL_EMOJI.get(record.levelname, "•") if self.use_emoji else ""
        return f"{emoji} {record.levelname} | {self.stage_name}: {record.getMessage()}"


class ErrorFileFormatter(logging.Formatter):
    """Formatter for error log files with timestamps and recovery actions."""

    def format(self, record):
        # Get recovery action if available
        recovery_action = getattr(record, "recovery_action", "")
        recovery_str = f" | Recovery: {recovery_action}" if recovery_action else ""

        # Format: [2026-03-02 10:30:45] ERROR (stage_name) error_type: message | Recovery: action
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        stage = getattr(record, "stage_name", "main")

        return f"[{timestamp}] {record.levelname} ({stage}) {record.getMessage()}{recovery_str}"


def get_logger(
    name: str = __name__,
    stage_name: str = "main",
    error_log_file: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Create or get a logger with console and optional error file handlers.

    Args:
        name: Logger name (typically __name__)
        stage_name: Pipeline stage name for context (e.g., "download", "audio")
        error_log_file: Path to error log file. Default: "logs/errors_{date}.log"
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured (avoid duplicate handlers)
    if len(logger.handlers) > 0:
        return logger

    logger.setLevel(level)

    # Console handler: INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = StageContextFormatter(stage_name=stage_name, use_emoji=True)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Error file handler: ERROR and WARNING only
    if error_log_file is None:
        error_log_file = f"logs/errors_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Create logs directory if needed
    log_dir = Path(error_log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Use RotatingFileHandler for daily rotation
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_log_file,
        when="midnight",
        interval=1,
        backupCount=7,  # Keep 7 days of logs
    )
    error_handler.setLevel(logging.WARNING)  # Only WARNING and ERROR
    error_formatter = ErrorFileFormatter()
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # Create a custom logger wrapper to store stage_name and handle recovery_action
    class EnhancedLogger:
        def __init__(self, base_logger, initial_stage):
            self._logger = base_logger
            self.stage_name = initial_stage
            self.error_log_file = error_log_file

        def set_stage(self, new_stage_name: str):
            """Update stage context for future logs."""
            self.stage_name = new_stage_name
            for handler in self._logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(
                    handler, logging.handlers.TimedRotatingFileHandler
                ):
                    if isinstance(handler.formatter, StageContextFormatter):
                        handler.formatter.stage_name = new_stage_name

        def info(self, msg: str):
            """Log info message."""
            self._logger.info(msg)

        def warning(self, msg: str, recovery_action: str = ""):
            """Log warning with optional recovery action."""
            record = self._logger.makeRecord(
                self._logger.name, logging.WARNING, "(unknown)", 0, msg, (), None
            )
            record.recovery_action = recovery_action
            record.stage_name = self.stage_name
            self._logger.handle(record)

        def error(
            self,
            msg: str,
            recovery_action: str = "",
            exception: Optional[Exception] = None,
        ):
            """Log error with optional recovery action and exception."""
            exc_info = None
            if exception:
                exc_info = (type(exception), exception, exception.__traceback__)

            record = self._logger.makeRecord(
                self._logger.name, logging.ERROR, "(unknown)", 0, msg, (), exc_info
            )
            record.recovery_action = recovery_action
            record.stage_name = self.stage_name
            self._logger.handle(record)

        def debug(self, msg: str):
            """Log debug message."""
            self._logger.debug(msg)

        # Delegate other attributes to base logger
        def __getattr__(self, name):
            return getattr(self._logger, name)

    # Return wrapped logger
    return EnhancedLogger(logger, stage_name)

    logger.setLevel(level)

    # Console handler: INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = StageContextFormatter(stage_name=stage_name, use_emoji=True)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Error file handler: ERROR and WARNING only
    if error_log_file is None:
        error_log_file = f"logs/errors_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Create logs directory if needed
    log_dir = Path(error_log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Use RotatingFileHandler for daily rotation
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_log_file,
        when="midnight",
        interval=1,
        backupCount=7,  # Keep 7 days of logs
    )
    error_handler.setLevel(logging.WARNING)  # Only WARNING and ERROR
    error_formatter = ErrorFileFormatter()
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # Store stage_name and log_file for later reference
    logger.stage_name = stage_name
    logger.error_log_file = error_log_file

    # Add helper methods to logger
    def set_stage(new_stage_name: str):
        """Update stage context for future logs."""
        logger.stage_name = new_stage_name
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.handlers.TimedRotatingFileHandler
            ):
                if isinstance(handler.formatter, StageContextFormatter):
                    handler.formatter.stage_name = new_stage_name

    logger.set_stage = set_stage

    # Override warning/error methods to capture recovery_action
    original_warning = logger.warning
    original_error = logger.error

    def warning_with_recovery(msg: str, recovery_action: str = "", *args, **kwargs):
        """Log warning with optional recovery action."""
        # Create a custom LogRecord with recovery_action
        record = logger.makeRecord(
            logger.name, logging.WARNING, "(unknown)", 0, msg, args, None
        )
        record.recovery_action = recovery_action
        record.stage_name = logger.stage_name
        logger.handle(record)

    def error_with_recovery(
        msg: str,
        recovery_action: str = "",
        exception: Optional[Exception] = None,
        *args,
        **kwargs,
    ):
        """Log error with optional recovery action and exception."""
        exc_info = None
        if exception:
            exc_info = (type(exception), exception, exception.__traceback__)

        # Create a custom LogRecord with recovery_action
        record = logger.makeRecord(
            logger.name, logging.ERROR, "(unknown)", 0, msg, args, exc_info
        )
        record.recovery_action = recovery_action
        record.stage_name = logger.stage_name
        logger.handle(record)

    logger.warning = warning_with_recovery
    logger.error = error_with_recovery

    return logger
