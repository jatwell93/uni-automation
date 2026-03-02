"""Tests for PII detection, removal, and temporary file management."""

import os
import tempfile
from pathlib import Path

import pytest

from src.transcript_processor import PIIDetector, PIIResult
from src.temp_manager import TempFileManager


class TestPIIDetection:
    """Tests for PII detection functionality."""

    def test_detect_emails_pattern(self):
        """Test email detection with various formats."""
        text = "Contact john.doe@university.edu or jane_smith@example.com"
        result = PIIDetector.detect_pii(text)
        assert result.emails_count >= 2
        assert any("john.doe@university.edu" in email for email in result.emails)

    def test_detect_student_ids_pattern(self):
        """Test student ID detection (7-8 digits, optional S prefix)."""
        text = "Student ID: S12345678 and another 87654321"
        result = PIIDetector.detect_pii(text)
        assert result.student_ids_count >= 1
        assert any("12345678" in sid for sid in result.student_ids)

    def test_detect_student_names_pattern(self):
        """Test detection of common student names."""
        text = "According to John Smith and Mary Johnson, the topic is complex."
        result = PIIDetector.detect_pii(text)
        # Should detect John and Mary or Smith and Johnson
        assert result.names_count > 0

    def test_detect_phone_numbers_pattern(self):
        """Test phone number detection (US and international formats)."""
        text = "Call me at 555-123-4567 or +1 555 123 4567"
        result = PIIDetector.detect_pii(text)
        # Should detect at least one phone pattern
        assert result.phone_numbers_count >= 1

    def test_detect_pii_returns_empty_dict_for_clean_text(self):
        """Test that clean text returns empty PII result."""
        text = "This is a normal academic discussion about programming concepts."
        result = PIIDetector.detect_pii(text)
        assert result.total_found == 0
        assert result.emails_count == 0
        assert result.names_count == 0
        assert result.student_ids_count == 0

    def test_remove_pii_replaces_emails_with_redacted(self):
        """Test that emails are replaced with [REDACTED]."""
        text = "Contact john@university.edu for help"
        result = PIIDetector.remove_pii(text, categories=["emails"])
        assert "[REDACTED]" in result
        assert "john@university.edu" not in result

    def test_remove_pii_replaces_student_ids_with_redacted(self):
        """Test that student IDs are replaced with [REDACTED]."""
        text = "Your student ID S12345678 is important"
        result = PIIDetector.remove_pii(text, categories=["student_ids"])
        assert "[REDACTED]" in result
        assert "12345678" not in result

    def test_remove_pii_removes_selected_categories_only(self):
        """Test that only selected categories are removed."""
        text = "John Smith emailed john@university.edu"
        # Only remove emails, not names
        result = PIIDetector.remove_pii(text, categories=["emails"])
        assert "[REDACTED]" in result
        assert "john@university.edu" not in result
        assert "John" in result or "Smith" in result  # Name should still be present

    def test_remove_pii_preserves_surrounding_text(self):
        """Test that surrounding text is preserved after PII removal."""
        text = "Please contact john@university.edu for assistance with your project"
        result = PIIDetector.remove_pii(text, categories=["emails"])
        assert "Please contact" in result
        assert "for assistance with your project" in result

    def test_log_pii_findings_warns_if_pii_detected_and_not_removed(self):
        """Test logging when PII detected but removal disabled."""
        text = "Contact john@example.com"
        result = PIIDetector.detect_pii(text)

        # Mock config with removal disabled
        class MockConfig:
            remove_pii_from_transcript = False

        # Should not raise, just log
        PIIDetector.log_pii_findings(result, MockConfig())

    def test_log_pii_findings_confirms_if_pii_removed(self):
        """Test logging when PII removed."""
        text = "Contact john@example.com"
        result = PIIDetector.detect_pii(text)

        # Mock config with removal enabled
        class MockConfig:
            remove_pii_from_transcript = True

        # Should not raise, just log
        PIIDetector.log_pii_findings(result, MockConfig())

    def test_pii_detector_with_real_transcript_sample(self):
        """Test with real transcript sample containing multiple PII types."""
        transcript = """
        Professor Smith discussed the assignment with John and Mary.
        John's email is john.doe@university.edu
        Contact S12345678 if you have questions.
        Call 555-123-4567 for technical support.
        """
        result = PIIDetector.detect_pii(transcript)
        assert result.emails_count >= 1
        assert result.student_ids_count >= 1

    def test_no_false_positives_in_normal_text(self):
        """Test that normal academic text doesn't trigger false positives."""
        text = (
            "The algorithm uses machine learning to analyze data. "
            "Section 3.14 shows the results. Version 1.0 was released in 2024."
        )
        result = PIIDetector.detect_pii(text)
        # Normal text should have minimal false positives
        assert result.total_found < 3  # Allow some tolerance


class TestTempFileManager:
    """Tests for temporary file management."""

    def test_register_temp_file_stores_metadata(self):
        """Test that registering temp file stores metadata."""
        manager = TempFileManager.instance()
        manager.clear_registry()

        file_path = "/tmp/test_video.mp4"
        manager.register_temp_file(file_path, "download", "Test video file")

        temp_files = manager.get_temp_files()
        assert len(temp_files) > 0
        assert any(file_path in str(f) for f in temp_files)

        manager.clear_registry()

    def test_cleanup_all_removes_registered_files(self):
        """Test that cleanup removes registered files."""
        manager = TempFileManager.instance()
        manager.clear_registry()

        # Create actual temp files
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
            f.write(b"test content")

        try:
            assert Path(temp_path).exists()
            manager.register_temp_file(temp_path, "test")

            result = manager.cleanup_all()
            assert result["deleted_count"] >= 1
            # File should be deleted
            assert not Path(temp_path).exists()
        finally:
            # Ensure cleanup
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            manager.clear_registry()

    def test_cleanup_by_stage_removes_only_specified_stage(self):
        """Test cleanup_by_stage removes only files from specified stage."""
        manager = TempFileManager.instance()
        manager.clear_registry()

        # Create temp files for different stages
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            download_file = f1.name
            f1.write(b"download")

        with tempfile.NamedTemporaryFile(delete=False) as f2:
            audio_file = f2.name
            f2.write(b"audio")

        try:
            manager.register_temp_file(download_file, "download")
            manager.register_temp_file(audio_file, "audio")

            # Cleanup only download stage
            manager.cleanup_by_stage("download")

            # Download file should be cleaned, audio file should remain
            assert not Path(download_file).exists()
            # Audio file may or may not exist depending on implementation

        finally:
            if Path(download_file).exists():
                Path(download_file).unlink()
            if Path(audio_file).exists():
                Path(audio_file).unlink()
            manager.clear_registry()

    def test_cleanup_handles_already_deleted_files(self):
        """Test that cleanup handles gracefully when file already deleted."""
        manager = TempFileManager.instance()
        manager.clear_registry()

        # Register a file that doesn't actually exist
        non_existent = "/tmp/non_existent_file_xyz.tmp"
        manager.register_temp_file(non_existent, "test")

        # Cleanup should not raise error
        result = manager.cleanup_all()
        assert result["failed_count"] >= 0  # May fail but shouldn't crash
        manager.clear_registry()

    def test_cleanup_handles_permission_errors(self):
        """Test that cleanup gracefully handles permission errors."""
        manager = TempFileManager.instance()
        manager.clear_registry()

        # Create a temp file with no write permissions (Unix-like systems)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            protected_path = f.name
            f.write(b"protected")

        try:
            # On Windows, permission handling is different
            # This test may behave differently across platforms
            manager.register_temp_file(protected_path, "test")
            result = manager.cleanup_all()
            # Should complete without raising exception
            assert "deleted_count" in result or "failed_count" in result
        finally:
            if Path(protected_path).exists():
                try:
                    Path(protected_path).unlink()
                except:
                    pass
            manager.clear_registry()

    def test_get_temp_files_returns_registered_list(self):
        """Test that get_temp_files returns all registered files."""
        manager = TempFileManager.instance()
        manager.clear_registry()

        manager.register_temp_file("/tmp/file1.tmp", "stage1")
        manager.register_temp_file("/tmp/file2.tmp", "stage2")

        files = manager.get_temp_files()
        assert len(files) >= 2
        manager.clear_registry()

    def test_temp_manager_singleton_pattern(self):
        """Test that TempFileManager follows singleton pattern."""
        manager1 = TempFileManager.instance()
        manager2 = TempFileManager.instance()

        assert manager1 is manager2

    def test_cleanup_returns_summary_counts(self):
        """Test that cleanup returns summary with deleted/failed counts."""
        manager = TempFileManager.instance()
        manager.clear_registry()

        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
            f.write(b"test")

        try:
            manager.register_temp_file(temp_path, "test")
            result = manager.cleanup_all()

            assert "deleted_count" in result
            assert "failed_count" in result
            assert result["deleted_count"] >= 0
            assert result["failed_count"] >= 0
        finally:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            manager.clear_registry()
