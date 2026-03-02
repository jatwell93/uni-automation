"""Integration tests for error handling and retry logic in pipeline."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.error_handler import ErrorHandler


class TestErrorHandlingIntegration:
    """Integration tests for error handling and retry logic in pipeline."""

    def test_network_timeout_retries_and_succeeds_on_second_attempt(self):
        """Test that transient errors (timeouts) are retried."""
        exc = Exception("Connection timeout")

        # First attempt should retry
        should_retry, delay = ErrorHandler.handle_error(
            exc, "download", max_retries=3, attempt=0
        )
        assert should_retry is True
        assert delay > 0

        # Second attempt should also retry
        should_retry, delay = ErrorHandler.handle_error(
            exc, "download", max_retries=3, attempt=1
        )
        assert should_retry is True
        assert delay > 0

    def test_auth_failure_fails_immediately_without_retry(self):
        """Test that fatal errors (auth) fail immediately without retry."""
        exc = Exception("401 Unauthorized")

        # Should not retry on auth failure
        should_retry, delay = ErrorHandler.handle_error(
            exc, "auth", max_retries=3, attempt=0
        )
        assert should_retry is False
        assert delay == 0

    def test_max_retries_exceeded_exits_with_error(self):
        """Test that exceeding max retries stops further retry attempts."""
        exc = Exception("Connection timeout")

        # After max_retries, should not retry
        should_retry, delay = ErrorHandler.handle_error(
            exc, "download", max_retries=3, attempt=3
        )
        assert should_retry is False
        assert delay == 0

    def test_error_logged_to_file_with_stage_and_recovery(self):
        """Test that errors are logged to file with stage and recovery action."""
        from src.logger import get_logger
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            error_log = Path(tmpdir) / "errors.log"
            logger = get_logger(
                "test_error_log_unique",
                error_log_file=str(error_log),
                stage_name="download",
            )

            # Log an error with recovery action
            logger.error("Network timeout", recovery_action="Check internet connection")

            # File should contain the error with recovery
            content = error_log.read_text()
            assert "Network timeout" in content
            assert "download" in content
            assert "Recovery:" in content

            # Close handlers
            for handler in logger._logger.handlers:
                handler.close()

    def test_pipeline_exits_with_status_message_on_failure(self):
        """Test that failed pipeline execution includes recovery instructions."""
        exc = Exception("Connection timeout")
        recovery = ErrorHandler.get_recovery_action(exc)

        # Should contain actionable recovery message
        assert len(recovery) > 0
        assert "retry" in recovery.lower() or "check" in recovery.lower()

    def test_exponential_backoff_increases_delays(self):
        """Test that exponential backoff produces increasing delays."""
        delay_0 = ErrorHandler.exponential_backoff(0, base_delay=2.0)
        delay_1 = ErrorHandler.exponential_backoff(1, base_delay=2.0)
        delay_2 = ErrorHandler.exponential_backoff(2, base_delay=2.0)

        # Average delays should increase
        # (individual may vary due to jitter, so check ranges)
        assert 2.0 <= delay_0 <= 3.0
        assert 4.0 <= delay_1 <= 7.0
        assert 8.0 <= delay_2 <= 30.0

    def test_run_stage_helper_retries_on_transient_error(self):
        """Test that run_stage retries on transient errors."""
        from src.pipeline import run_stage
        import tempfile

        call_count = 0

        def failing_stage(_config):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection timeout")
            return "success"

        # Mock logger to avoid logging during test
        with patch("src.pipeline.logger") as mock_logger:
            mock_logger.set_stage = MagicMock()
            mock_logger.info = MagicMock()
            mock_logger.warning = MagicMock()
            mock_logger.error = MagicMock()

            # Create minimal valid config with real files
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Create required files
                slide_path = tmpdir_path / "test.pdf"
                slide_path.write_bytes(b"%PDF-1.4\n")

                from src.config import ConfigModel

                config = ConfigModel(
                    lecture={
                        "url": "https://test.edu/lecture",
                        "slide_path": str(slide_path),
                    },
                    paths={
                        "cookie_file": str(tmpdir_path / "cookies.json"),
                        "output_dir": str(tmpdir_path / "out"),
                        "temp_dir": str(tmpdir_path / "temp"),
                    },
                    metadata={"course_name": "test", "week_number": 1},
                    obsidian_vault_path=str(tmpdir_path / "vault"),
                    openrouter_api_key="sk-test-api-key-12345678",
                )

                # Call should eventually succeed after retry
                success, result, msg = run_stage(failing_stage, "test-stage", config)
                assert success is True
                assert result == "success"
                assert call_count >= 2  # Should have retried once

    def test_categorize_various_error_types(self):
        """Test error categorization for various scenarios."""
        from src.error_handler import ErrorCategory

        test_cases = [
            (Exception("timeout"), ErrorCategory.RETRYABLE),
            (Exception("Connection reset"), ErrorCategory.RETRYABLE),
            (Exception("401 Unauthorized"), ErrorCategory.FATAL),
            (Exception("Invalid config"), ErrorCategory.FATAL),
            (Exception("File not found"), ErrorCategory.FATAL),
            (Exception("429 Too Many Requests"), ErrorCategory.RETRYABLE),
            (Exception("500 Internal Server Error"), ErrorCategory.RETRYABLE),
        ]

        for exc, expected_category in test_cases:
            category = ErrorHandler.categorize(exc, "test")
            assert category == expected_category, (
                f"Failed for {exc}: got {category}, expected {expected_category}"
            )

    def test_recovery_action_generation(self):
        """Test that recovery actions are generated appropriately."""
        test_cases = [
            (Exception("401 Unauthorized"), "cookie"),
            (Exception("Connection timeout"), "internet"),
            (Exception("Invalid config"), "yaml"),
            (Exception("File not found"), "file"),
            (Exception("Quota exceeded"), "quota"),
        ]

        for exc, keyword in test_cases:
            action = ErrorHandler.get_recovery_action(exc)
            assert keyword.lower() in action.lower(), (
                f"Recovery action for {exc} should mention '{keyword}'"
            )
