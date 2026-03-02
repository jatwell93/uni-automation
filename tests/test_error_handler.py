"""
Unit tests for ErrorHandler error categorization, backoff, and retry logic.
"""

import pytest
from src.error_handler import ErrorHandler, ErrorCategory, RetryableError, FatalError


class TestErrorCategorization:
    """Tests for error type categorization."""

    def test_categorize_network_timeout_as_retryable(self):
        """Network timeout should be retryable."""
        exc = Exception("Connection timeout")
        category = ErrorHandler.categorize(exc, "download")
        assert category == ErrorCategory.RETRYABLE

    def test_categorize_connection_reset_as_retryable(self):
        """Connection reset should be retryable."""
        exc = Exception("Connection reset by peer")
        category = ErrorHandler.categorize(exc, "download")
        assert category == ErrorCategory.RETRYABLE

    def test_categorize_auth_failure_as_fatal(self):
        """401/unauthorized should be fatal."""
        exc = Exception("401 Unauthorized")
        category = ErrorHandler.categorize(exc, "auth")
        assert category == ErrorCategory.FATAL

    def test_categorize_invalid_cookie_as_fatal(self):
        """Invalid cookie error should be fatal."""
        exc = Exception("Invalid auth cookie")
        category = ErrorHandler.categorize(exc, "auth")
        assert category == ErrorCategory.FATAL

    def test_categorize_token_expired_as_fatal(self):
        """Expired token should be fatal."""
        exc = Exception("Token expired")
        category = ErrorHandler.categorize(exc, "auth")
        assert category == ErrorCategory.FATAL

    def test_categorize_invalid_config_as_fatal(self):
        """Invalid config error should be fatal."""
        exc = Exception("Invalid config: missing required field")
        category = ErrorHandler.categorize(exc, "config")
        assert category == ErrorCategory.FATAL

    def test_categorize_rate_limit_as_retryable(self):
        """Rate limit (429) should be retryable."""
        exc = Exception("429 Too Many Requests")
        category = ErrorHandler.categorize(exc, "llm")
        assert category == ErrorCategory.RETRYABLE

    def test_categorize_quota_exceeded_as_retryable(self):
        """Quota exceeded should be retryable."""
        exc = Exception("Quota exceeded")
        category = ErrorHandler.categorize(exc, "llm")
        assert category == ErrorCategory.RETRYABLE

    def test_categorize_file_not_found_as_fatal(self):
        """File not found should be fatal."""
        exc = Exception("File not found: /path/to/file")
        category = ErrorHandler.categorize(exc, "input")
        assert category == ErrorCategory.FATAL

    def test_categorize_api_5xx_as_retryable(self):
        """API 500 errors should be retryable."""
        exc = Exception("500 Internal Server Error")
        category = ErrorHandler.categorize(exc, "llm")
        assert category == ErrorCategory.RETRYABLE

    def test_categorize_service_unavailable_as_retryable(self):
        """Service unavailable should be retryable."""
        exc = Exception("Service unavailable")
        category = ErrorHandler.categorize(exc, "llm")
        assert category == ErrorCategory.RETRYABLE

    def test_categorize_unknown_as_retryable_default(self):
        """Unknown errors default to retryable (assume transient)."""
        exc = Exception("Something went wrong")
        category = ErrorHandler.categorize(exc, "unknown")
        assert category == ErrorCategory.RETRYABLE


class TestExponentialBackoff:
    """Tests for exponential backoff delay computation."""

    def test_exponential_backoff_increasing_delays(self):
        """Backoff delays should increase exponentially."""
        delay_0 = ErrorHandler.exponential_backoff(0, base_delay=2.0, max_delay=30.0)
        delay_1 = ErrorHandler.exponential_backoff(1, base_delay=2.0, max_delay=30.0)
        delay_2 = ErrorHandler.exponential_backoff(2, base_delay=2.0, max_delay=30.0)

        # Delays should be increasing (within range)
        assert 2.0 <= delay_0 <= 3.0  # 2 + jitter up to 1
        assert 4.0 <= delay_1 <= 7.0  # 4 + jitter up to 2
        assert 8.0 <= delay_2 <= 30.0  # 8 + jitter up to 4, but capped at 30

    def test_exponential_backoff_jitter_adds_randomness(self):
        """Backoff delays should have randomness (jitter)."""
        delays = [ErrorHandler.exponential_backoff(1) for _ in range(10)]

        # All delays should be different (with very high probability)
        assert len(set(delays)) > 1, "Jitter should produce varied delays"

    def test_exponential_backoff_max_delay_capped(self):
        """Backoff should cap at max_delay."""
        delay_10 = ErrorHandler.exponential_backoff(10, base_delay=2.0, max_delay=30.0)

        # Should not exceed max_delay + jitter
        assert delay_10 <= 45.0  # 30 + 50% jitter

    def test_exponential_backoff_attempt_0(self):
        """Attempt 0 should give 2-3 second delay."""
        delays = [ErrorHandler.exponential_backoff(0) for _ in range(5)]

        for delay in delays:
            assert 2.0 <= delay <= 3.0


class TestRetryLogic:
    """Tests for handle_error retry decision logic."""

    def test_handle_error_returns_retry_true_for_retryable(self):
        """Retryable error within max_retries should return (True, delay)."""
        exc = Exception("Connection timeout")
        should_retry, delay = ErrorHandler.handle_error(
            exc, "download", max_retries=3, attempt=0
        )

        assert should_retry is True
        assert delay > 0

    def test_handle_error_returns_retry_false_for_fatal(self):
        """Fatal error should return (False, 0)."""
        exc = Exception("401 Unauthorized")
        should_retry, delay = ErrorHandler.handle_error(
            exc, "auth", max_retries=3, attempt=0
        )

        assert should_retry is False
        assert delay == 0

    def test_handle_error_respects_max_retries(self):
        """Should not retry after max_retries exceeded."""
        exc = Exception("Connection timeout")

        # Should retry at attempt 0-2
        assert (
            ErrorHandler.handle_error(exc, "download", max_retries=3, attempt=0)[0]
            is True
        )
        assert (
            ErrorHandler.handle_error(exc, "download", max_retries=3, attempt=1)[0]
            is True
        )
        assert (
            ErrorHandler.handle_error(exc, "download", max_retries=3, attempt=2)[0]
            is True
        )

        # Should NOT retry at attempt 3
        should_retry, delay = ErrorHandler.handle_error(
            exc, "download", max_retries=3, attempt=3
        )
        assert should_retry is False
        assert delay == 0


class TestRecoveryActions:
    """Tests for recovery action message generation."""

    def test_recovery_action_auth_failure(self):
        """Auth failure should suggest cookie refresh."""
        exc = Exception("401 Unauthorized")
        action = ErrorHandler.get_recovery_action(exc)

        assert "cookie" in action.lower() or "auth" in action.lower()

    def test_recovery_action_config_error(self):
        """Config error should suggest checking YAML."""
        exc = Exception("Invalid config: missing required field")
        action = ErrorHandler.get_recovery_action(exc)

        assert (
            "yaml" in action.lower()
            or "config" in action.lower()
            or "field" in action.lower()
        )

    def test_recovery_action_network_timeout(self):
        """Network timeout should suggest checking internet."""
        exc = Exception("Connection timeout")
        action = ErrorHandler.get_recovery_action(exc)

        assert (
            "internet" in action.lower()
            or "connection" in action.lower()
            or "timeout" in action.lower()
        )

    def test_recovery_action_quota_error(self):
        """Quota error should suggest checking quota."""
        exc = Exception("Quota exceeded")
        action = ErrorHandler.get_recovery_action(exc)

        assert "quota" in action.lower() or "retry" in action.lower()

    def test_recovery_action_file_error(self):
        """File not found should suggest checking path."""
        exc = Exception("File not found: /path/to/file")
        action = ErrorHandler.get_recovery_action(exc)

        assert "file" in action.lower() or "path" in action.lower()


class TestCustomExceptions:
    """Tests for custom RetryableError and FatalError exceptions."""

    def test_retryable_error_stores_metadata(self):
        """RetryableError should store error metadata."""
        exc = RetryableError(
            "Connection timeout", "download", "Check internet connection"
        )

        assert exc.error_message == "Connection timeout"
        assert exc.stage_name == "download"
        assert exc.recovery_action == "Check internet connection"

    def test_fatal_error_stores_metadata(self):
        """FatalError should store error metadata."""
        exc = FatalError("Invalid config", "config", "Check YAML syntax")

        assert exc.error_message == "Invalid config"
        assert exc.stage_name == "config"
        assert exc.recovery_action == "Check YAML syntax"

    def test_retryable_error_is_exception(self):
        """RetryableError should be an Exception."""
        exc = RetryableError("Test", "stage", "action")
        assert isinstance(exc, Exception)

    def test_fatal_error_is_exception(self):
        """FatalError should be an Exception."""
        exc = FatalError("Test", "stage", "action")
        assert isinstance(exc, Exception)
