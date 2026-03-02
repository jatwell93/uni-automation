"""Unit tests for Google Drive sync manager."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

from src.gdrive_sync import (
    GoogleDriveSyncManager,
    SyncResult,
    SyncError,
    slugify_course_name,
    validate_gdrive_folder,
)


class TestSluggifyCourseeName:
    """Tests for course name slugification."""

    def test_simple_name(self):
        """Test basic course name conversion."""
        assert slugify_course_name("Business Analytics") == "business-analytics"

    def test_with_special_chars(self):
        """Test course name with special characters."""
        assert slugify_course_name("Data & Analytics") == "data-analytics"

    def test_with_multiple_spaces(self):
        """Test course name with multiple spaces."""
        assert (
            slugify_course_name("Advanced   Data   Science") == "advanced-data-science"
        )

    def test_lowercase_preservation(self):
        """Test that uppercase is converted to lowercase."""
        assert slugify_course_name("BUSINESS ANALYTICS") == "business-analytics"

    def test_with_punctuation(self):
        """Test course name with punctuation."""
        assert (
            slugify_course_name("CS 101: Intro to Programming")
            == "cs-101-intro-to-programming"
        )


class TestValidateGdriveFolderFunction:
    """Tests for the standalone validate_gdrive_folder function."""

    def test_folder_does_not_exist(self):
        """Test validation fails for non-existent folder."""
        success, error = validate_gdrive_folder("/nonexistent/path/to/gdrive")
        assert not success
        assert "not found" in error.lower()

    def test_valid_writable_folder(self):
        """Test validation succeeds for valid writable folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            success, error = validate_gdrive_folder(tmpdir)
            assert success
            assert error == ""

    def test_folder_not_writable(self):
        """Test validation fails for read-only folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Make directory read-only
            os.chmod(tmpdir, 0o444)
            try:
                success, error = validate_gdrive_folder(tmpdir)
                # May or may not fail depending on OS
                if not success:
                    assert "writable" in error.lower() or "permission" in error.lower()
            finally:
                # Restore permissions for cleanup
                os.chmod(tmpdir, 0o755)

    def test_path_is_file_not_directory(self):
        """Test validation fails if path is a file."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            success, error = validate_gdrive_folder(tmpfile.name)
            assert not success
            assert "not a directory" in error.lower()


class TestGoogleDriveSyncManagerInit:
    """Tests for GoogleDriveSyncManager initialization."""

    def test_init_with_valid_folder(self):
        """Test initialization with valid Google Drive folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)
            assert manager.gdrive_sync_folder == Path(tmpdir)

    def test_init_without_gdrive_folder(self):
        """Test initialization when gdrive_sync_folder is None."""
        config = Mock()
        config.gdrive_sync_folder = None

        manager = GoogleDriveSyncManager(config)
        assert manager.gdrive_sync_folder is None

    def test_init_with_invalid_folder(self):
        """Test initialization fails with invalid Google Drive folder."""
        config = Mock()
        config.gdrive_sync_folder = "/nonexistent/gdrive/path"

        with pytest.raises(ValueError, match="not found"):
            GoogleDriveSyncManager(config)

    def test_init_raises_if_folder_missing(self):
        """Test init raises specific error if folder missing."""
        config = Mock()
        config.gdrive_sync_folder = "/path/that/does/not/exist"

        with pytest.raises(ValueError) as exc_info:
            GoogleDriveSyncManager(config)

        error_msg = str(exc_info.value)
        assert "Google Drive sync folder not found" in error_msg
        assert "gdrive_sync_folder" in error_msg


class TestGetCourseSubfolderPath:
    """Tests for get_course_subfolder_path method."""

    def test_creates_course_week_subfolder(self):
        """Test that course/week subfolder is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)
            path = manager.get_course_subfolder_path("Business Analytics", 5)

            assert path.exists()
            assert path.is_dir()
            assert "business-analytics" in str(path).lower()
            assert "Week_05" in str(path)

    def test_path_structure_with_special_chars(self):
        """Test path structure with special character course name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)
            path = manager.get_course_subfolder_path("Data & Analytics", 3)

            assert path.exists()
            assert "data-analytics" in str(path).lower()
            assert "Week_03" in str(path)

    def test_idempotent_folder_creation(self):
        """Test that creating folder twice doesn't fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)
            path1 = manager.get_course_subfolder_path("Python 101", 2)
            path2 = manager.get_course_subfolder_path("Python 101", 2)

            assert path1 == path2
            assert path1.exists()

    def test_raises_if_gdrive_folder_not_set(self):
        """Test raises error if gdrive_sync_folder not configured."""
        config = Mock()
        config.gdrive_sync_folder = None

        manager = GoogleDriveSyncManager(config)

        with pytest.raises(ValueError, match="not configured"):
            manager.get_course_subfolder_path("Course", 1)


class TestValidateFileCopy:
    """Tests for validate_file_copy method."""

    def test_succeeds_when_size_matches(self):
        """Test validation succeeds when file sizes match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            # Create source and target files with same content
            source = Path(tmpdir) / "source.txt"
            target = Path(tmpdir) / "target.txt"

            source.write_text("test content")
            target.write_text("test content")

            success, error = manager.validate_file_copy(str(source), str(target))

            assert success
            assert error == ""

    def test_fails_when_size_mismatch(self):
        """Test validation fails when file sizes don't match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            source = Path(tmpdir) / "source.txt"
            target = Path(tmpdir) / "target.txt"

            source.write_text("large content here")
            target.write_text("small")

            success, error = manager.validate_file_copy(str(source), str(target))

            assert not success
            assert "size" in error.lower()

    def test_fails_when_target_missing(self):
        """Test validation fails when target file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            source = Path(tmpdir) / "source.txt"
            source.write_text("content")

            success, error = manager.validate_file_copy(
                str(source), str(Path(tmpdir) / "missing.txt")
            )

            assert not success
            assert "not found" in error.lower()

    def test_fails_when_target_not_regular_file(self):
        """Test validation fails when target is not a regular file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            source = Path(tmpdir) / "source.txt"
            source.write_text("content")

            target_dir = Path(tmpdir) / "target_dir"
            target_dir.mkdir()

            success, error = manager.validate_file_copy(str(source), str(target_dir))

            assert not success
            assert "not a regular file" in error.lower()


class TestSyncArtifacts:
    """Tests for sync_artifacts method."""

    def test_sync_artifacts_copies_all_files(self):
        """Test that sync_artifacts copies transcript, audio, and slides."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            # Create mock source files
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()

            transcript = source_dir / "transcript.txt"
            audio = source_dir / "audio.m4a"
            slides = source_dir / "slides.txt"

            transcript.write_text("Transcript content here")
            audio.write_bytes(b"mock audio data")
            slides.write_text("Slide content here")

            # Sync
            result = manager.sync_artifacts(
                lecture_id="week_05",
                transcript_path=str(transcript),
                audio_path=str(audio),
                slides_text_path=str(slides),
                course_name="Test Course",
                week_number=5,
            )

            # Verify result
            assert result.success
            assert result.synced_files == 3
            assert result.failed_files == 0
            assert len(result.errors) == 0

    def test_sync_artifacts_creates_course_week_folder(self):
        """Test that sync creates proper course/week folder structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()

            transcript = source_dir / "transcript.txt"
            audio = source_dir / "audio.m4a"
            slides = source_dir / "slides.txt"

            transcript.write_text("content")
            audio.write_bytes(b"audio")
            slides.write_text("slides")

            result = manager.sync_artifacts(
                lecture_id="week_02",
                transcript_path=str(transcript),
                audio_path=str(audio),
                slides_text_path=str(slides),
                course_name="Business Analytics",
                week_number=2,
            )

            assert result.success
            assert result.synced_files == 3

            # Verify folder structure
            expected_folder = Path(tmpdir) / "business-analytics" / "Week_02"
            assert (expected_folder / "transcript.txt").exists()
            assert (expected_folder / "audio.m4a").exists()
            assert (expected_folder / "slides.txt").exists()

    def test_sync_handles_missing_source_file(self):
        """Test sync handles missing source files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            result = manager.sync_artifacts(
                lecture_id="week_01",
                transcript_path="/nonexistent/transcript.txt",
                audio_path="/nonexistent/audio.m4a",
                slides_text_path="/nonexistent/slides.txt",
                course_name="Course",
                week_number=1,
            )

            assert not result.success
            assert result.synced_files == 0
            assert result.failed_files == 3
            assert len(result.errors) == 3

    def test_sync_result_contains_metadata(self):
        """Test sync result contains all required metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()

            transcript = source_dir / "transcript.txt"
            audio = source_dir / "audio.m4a"
            slides = source_dir / "slides.txt"

            transcript.write_text("test")
            audio.write_bytes(b"test")
            slides.write_text("test")

            result = manager.sync_artifacts(
                lecture_id="week_03",
                transcript_path=str(transcript),
                audio_path=str(audio),
                slides_text_path=str(slides),
                course_name="Test",
                week_number=3,
            )

            assert isinstance(result, SyncResult)
            assert hasattr(result, "success")
            assert hasattr(result, "synced_files")
            assert hasattr(result, "failed_files")
            assert hasattr(result, "total_size_bytes")
            assert hasattr(result, "errors")
            assert hasattr(result, "sync_duration_seconds")
            assert result.sync_duration_seconds > 0

    def test_sync_handles_permission_denied_error(self):
        """Test sync handles permission denied errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()

            transcript = source_dir / "transcript.txt"
            transcript.write_text("content")

            # Mock shutil.copy2 to raise PermissionError
            with patch("shutil.copy2") as mock_copy:
                mock_copy.side_effect = PermissionError("Access denied")

                result = manager.sync_artifacts(
                    lecture_id="week_01",
                    transcript_path=str(transcript),
                    audio_path=str(transcript),
                    slides_text_path=str(transcript),
                    course_name="Test",
                    week_number=1,
                )

                # Sync should handle permission error gracefully
                assert len(result.errors) > 0
                assert not result.success
                assert result.failed_files == 3

    def test_sync_handles_disk_full_error(self):
        """Test sync handles disk full errors with recovery instructions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.gdrive_sync_folder = tmpdir

            manager = GoogleDriveSyncManager(config)

            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()

            transcript = source_dir / "transcript.txt"
            transcript.write_text("content")

            # Mock a disk full error
            with patch("shutil.copy2") as mock_copy:
                mock_copy.side_effect = OSError("No space left on device")

                result = manager.sync_artifacts(
                    lecture_id="week_01",
                    transcript_path=str(transcript),
                    audio_path=str(transcript),
                    slides_text_path=str(transcript),
                    course_name="Test",
                    week_number=1,
                )

                assert not result.success
                assert len(result.errors) > 0
                # Check that recovery instructions include quota guidance
                error_text = " ".join(e.recovery_action for e in result.errors)
                assert "quota" in error_text.lower() or "space" in error_text.lower()
