"""Tests for the validator module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess

from src.validator import validate_video
from src.models import ValidationResult


class TestValidateVideo:
    """Tests for validate_video function."""

    def test_validate_video_success(self):
        """Test successful video validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"

            # Create a fake video file with some content
            video_path.write_bytes(
                b"fake video content" * (50 * 1024 * 1024 // 18)
            )  # ~50MB

            with patch("src.validator.shutil.which") as mock_which:
                mock_which.return_value = "ffprobe"

                with patch("src.validator.subprocess.run") as mock_run:
                    # First call returns duration and size
                    mock_result1 = Mock()
                    mock_result1.returncode = 0
                    mock_result1.stdout = "120.5\n52428800"  # 120.5 seconds, 50MB
                    mock_result1.stderr = ""

                    # Second call returns codec
                    mock_result2 = Mock()
                    mock_result2.returncode = 0
                    mock_result2.stdout = "h264"
                    mock_result2.stderr = ""

                    mock_run.side_effect = [mock_result1, mock_result2]

                    result = validate_video(
                        video_path, min_size_mb=10, min_duration_sec=60
                    )

                    assert result.success is True
                    assert result.duration_seconds == 120.5
                    assert result.file_size_bytes == 52428800
                    assert result.codec_name == "h264"

    def test_validate_video_not_found(self):
        """Test error when video file not found."""
        video_path = Path("/nonexistent/video.mp4")

        result = validate_video(video_path)

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_validate_video_duration_too_short(self):
        """Test error when video duration below minimum."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.write_bytes(b"fake video" * (150 * 1024 * 1024 // 10))  # ~150MB

            with patch("src.validator.shutil.which") as mock_which:
                mock_which.return_value = "ffprobe"

                with patch("src.validator.subprocess.run") as mock_run:
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = (
                        "30.0\n157286400"  # 30 seconds (below 60s minimum), 150MB
                    )
                    mock_result.stderr = ""
                    mock_run.return_value = mock_result

                    result = validate_video(
                        video_path, min_size_mb=100, min_duration_sec=60
                    )

                    assert result.success is False
                    assert "duration" in result.error.lower()

    def test_validate_video_size_too_small(self):
        """Test error when file size below minimum."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.write_bytes(b"small video" * (10 * 1024 * 1024 // 11))  # ~10MB

            with patch("src.validator.shutil.which") as mock_which:
                mock_which.return_value = "ffprobe"

                with patch("src.validator.subprocess.run") as mock_run:
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = (
                        "120.0\n10485760"  # 120 seconds, 10MB (below 100MB minimum)
                    )
                    mock_result.stderr = ""
                    mock_run.return_value = mock_result

                    result = validate_video(
                        video_path, min_size_mb=100, min_duration_sec=60
                    )

                    assert result.success is False
                    assert (
                        "size" in result.error.lower()
                        or "below" in result.error.lower()
                    )

    def test_ffprobe_not_installed(self):
        """Test error when ffprobe is not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.write_bytes(b"fake video" * 1000)

            with patch("src.validator.shutil.which") as mock_which:
                mock_which.return_value = None

                with patch.dict("os.environ", {}, clear=False):
                    result = validate_video(video_path)

                    assert result.success is False
                    assert "ffmpeg" in result.error.lower()
                    assert "not installed" in result.error.lower()
                    assert "gyan.dev" in result.error

    def test_validate_video_timeout(self):
        """Test timeout during ffprobe validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.write_bytes(b"fake video" * 1000)

            with patch("src.validator.shutil.which") as mock_which:
                mock_which.return_value = "ffprobe"

                with patch("src.validator.subprocess.run") as mock_run:
                    # First call times out
                    mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 30)

                    result = validate_video(video_path)

                    assert result.success is False
                    assert "timeout" in result.error.lower()

    def test_validate_video_ffprobe_error(self):
        """Test ffprobe subprocess error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.write_bytes(b"not a real video file")

            with patch("src.validator.shutil.which") as mock_which:
                mock_which.return_value = "ffprobe"

                with patch("src.validator.subprocess.run") as mock_run:
                    mock_result = Mock()
                    mock_result.returncode = 1
                    mock_result.stdout = ""
                    mock_result.stderr = "Invalid data found"
                    mock_run.return_value = mock_result

                    result = validate_video(video_path)

                    assert result.success is False
                    assert (
                        "ffmpeg error" in result.error.lower()
                        or "corrupted" in result.error.lower()
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
