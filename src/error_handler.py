"""
Error handling system for pipeline resilience.

Provides error categorization (retryable vs fatal), exponential backoff computation,
and intelligent retry decision logic for transient vs permanent failures.
"""

import random
import time
import re
from enum import Enum
from typing import Tuple


class ErrorCategory(Enum):
    """Classification of errors into retryable (transient) vs fatal (permanent)."""

    RETRYABLE = "retryable"
    FATAL = "fatal"


class RetryableError(Exception):
    """Error that should be retried (transient failure like timeout or connection reset)."""

    def __init__(self, error_message: str, stage_name: str, recovery_action: str):
        self.error_message = error_message
        self.stage_name = stage_name
        self.recovery_action = recovery_action
        super().__init__(error_message)


class FatalError(Exception):
    """Error that should not be retried (permanent failure like invalid config or auth)."""

    def __init__(self, error_message: str, stage_name: str, recovery_action: str):
        self.error_message = error_message
        self.stage_name = stage_name
        self.recovery_action = recovery_action
        super().__init__(error_message)


class ErrorHandler:
    """
    Intelligent error categorization and retry decision making.

    Determines whether errors are transient (retry with backoff) or fatal (fail fast).
    Computes exponential backoff delays with jitter to prevent thundering herd.
    """

    @staticmethod
    def categorize(exception: Exception, stage_name: str) -> ErrorCategory:
        """
        Classify an exception as retryable or fatal based on type and message patterns.

        Args:
            exception: The exception to categorize
            stage_name: Name of pipeline stage for context

        Returns:
            ErrorCategory.RETRYABLE or ErrorCategory.FATAL
        """
        exc_str = str(exception).lower()
        exc_type = type(exception).__name__

        # Network errors - RETRYABLE
        network_patterns = [
            r"timeout",
            r"connection reset",
            r"connection refused",
            r"connection aborted",
            r"broken pipe",
            r"dns.*error",
            r"name not resolved",
            r"network unreachable",
            r"connection error",
            r"no host",
            r"temporary failure",
        ]

        for pattern in network_patterns:
            if re.search(pattern, exc_str):
                return ErrorCategory.RETRYABLE

        # Auth errors - FATAL
        auth_patterns = [
            r"401",
            r"unauthorized",
            r"invalid.*auth",
            r"token.*expired",
            r"authentication.*failed",
            r"invalid.*cookie",
            r"invalid.*credential",
            r"forbidden",
            r"403",
        ]

        for pattern in auth_patterns:
            if re.search(pattern, exc_str):
                return ErrorCategory.FATAL

        # Config errors - FATAL
        config_patterns = [
            r"missing.*field",
            r"invalid.*config",
            r"required.*field",
            r"invalid.*value",
            r"validation.*error",
            r"invalid.*yaml",
            r"invalid.*json",
        ]

        for pattern in config_patterns:
            if re.search(pattern, exc_str):
                return ErrorCategory.FATAL

        # File errors - FATAL
        file_patterns = [
            r"file not found",
            r"no such file",
            r"filenotfounderror",
            r"permission denied",
            r"access denied",
        ]

        for pattern in file_patterns:
            if re.search(pattern, exc_str):
                return ErrorCategory.FATAL

        # Quota/rate limit errors - RETRYABLE
        quota_patterns = [
            r"429",
            r"quota.*exceeded",
            r"rate.*limit",
            r"too many requests",
            r"quota",
        ]

        for pattern in quota_patterns:
            if re.search(pattern, exc_str):
                return ErrorCategory.RETRYABLE

        # API errors (5xx) - RETRYABLE (usually transient)
        api_patterns = [
            r"50[0-9]",
            r"service.*unavailable",
            r"server error",
            r"internal error",
        ]

        for pattern in api_patterns:
            if re.search(pattern, exc_str):
                return ErrorCategory.RETRYABLE

        # Default: assume transient, let max_retries control
        return ErrorCategory.RETRYABLE

    @staticmethod
    def exponential_backoff(
        attempt: int, base_delay: float = 2.0, max_delay: float = 30.0
    ) -> float:
        """
        Compute exponential backoff delay with jitter.

        Delays: attempt 0 → 2-3s, attempt 1 → 4-7s, attempt 2 → 8-30s
        Formula: base_delay * (2^attempt) + random jitter

        Args:
            attempt: 0-indexed attempt number
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds

        Returns:
            Delay in seconds
        """
        # Exponential growth: 2^0=1, 2^1=2, 2^2=4, 2^3=8
        exponential = base_delay * (2**attempt)

        # Cap to max_delay
        capped = min(exponential, max_delay)

        # Add random jitter (up to 50% of delay)
        jitter = random.uniform(0, capped * 0.5)

        return capped + jitter

    @staticmethod
    def handle_error(
        exception: Exception, stage_name: str, max_retries: int = 3, attempt: int = 0
    ) -> Tuple[bool, float]:
        """
        Determine if an error should trigger a retry and compute backoff delay.

        Args:
            exception: The exception to handle
            stage_name: Name of pipeline stage
            max_retries: Maximum retry attempts allowed
            attempt: Current attempt number (0-indexed)

        Returns:
            Tuple of (should_retry: bool, delay_seconds: float)
            - (True, delay) if error is retryable and attempt < max_retries
            - (False, 0) if error is fatal or max_retries exceeded
        """
        category = ErrorHandler.categorize(exception, stage_name)

        if category == ErrorCategory.FATAL:
            return (False, 0)

        # Retryable error
        if attempt < max_retries:
            delay = ErrorHandler.exponential_backoff(attempt)
            return (True, delay)
        else:
            # Exceeded max retries
            return (False, 0)

    @staticmethod
    def get_recovery_action(exception: Exception) -> str:
        """
        Generate recovery action message based on exception type.

        Args:
            exception: The exception to generate action for

        Returns:
            Human-readable recovery action string
        """
        exc_str = str(exception).lower()

        # Auth failures
        if any(
            pat in exc_str
            for pat in ["401", "unauthorized", "token expired", "invalid cookie"]
        ):
            return "Refresh cookies from browser, update config, and retry"

        # Config errors
        if any(
            pat in exc_str
            for pat in [
                "invalid config",
                "missing field",
                "required field",
                "invalid yaml",
            ]
        ):
            return "Check YAML syntax and required fields, fix error, and retry"

        # Network timeouts
        if any(pat in exc_str for pat in ["timeout", "connection"]):
            return "Check internet connection, retry stage, or increase timeout"

        # Quota errors
        if any(pat in exc_str for pat in ["quota", "429", "rate limit"]):
            return "Check OpenRouter quota, wait and retry, or switch model"

        # File errors
        if any(
            pat in exc_str
            for pat in ["file not found", "no such file", "permission denied"]
        ):
            return "Check file path in config, ensure file exists, and retry"

        # Default
        return "Check error details, fix issue, and retry"
