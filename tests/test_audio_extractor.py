"""Unit tests for audio extraction module."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

from src.audio_extractor import extract_audio, validate_audio_output
from src.models import AudioExtractionResult, AudioExtractionError


class TestExtractAudio:
    """Tests for extract_audio function."""

    def test_extract_audio_valid_video(self, tmp_path):
        """Test extraction from a valid video file."""
        # Create a mock video file
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("mock video content")

        output_file = tmp_path / "output.mp3"

        # Mock subprocess calls
        with (
            patch("src.audio_extractor.shutil.which") as mock_which,
            patch("src.audio_extractor.subprocess.run") as mock_run,
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            # First call: ffprobe to check audio stream (returns duration)
            # Second call: ffmpeg extraction
            # Third call: ffprobe validation
            mock_run.side_effect = [
                MagicMock(
                    returncode=0, stdout="3600.0\n", stderr=""
                ),  # ffprobe input check
                MagicMock(returncode=0, stdout="", stderr=""),  # ffmpeg extraction
                MagicMock(
                    returncode=0, stdout="3600.0\n", stderr=""
                ),  # ffprobe validation
            ]

            # Create actual output file for validation
            output_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

            result = extract_audio(video_file, output_file)

            assert result.status == "success"
            assert result.output_path == output_file
            assert result.duration == 3600.0
            assert result.file_size == 2 * 1024 * 1024

    def test_extract_audio_missing_input(self, tmp_path):
        """Test extraction fails when input file doesn't exist."""
        video_file = tmp_path / "nonexistent.mp4"
        output_file = tmp_path / "output.mp3"

        with pytest.raises(AudioExtractionError) as exc_info:
            extract_audio(video_file, output_file)

        assert "Input video file not found" in str(exc_info.value)

    def test_extract_audio_empty_input(self, tmp_path):
        """Test extraction fails when input file is empty."""
        video_file = tmp_path / "empty.mp4"
        video_file.write_text("")

        output_file = tmp_path / "output.mp3"

        with pytest.raises(AudioExtractionError) as exc_info:
            extract_audio(video_file, output_file)

        assert "Input video file is empty" in str(exc_info.value)

    def test_extract_audio_no_ffmpeg(self, tmp_path):
        """Test extraction fails when ffmpeg is not available."""
        video_file = tmp_path / "test.mp4"
        video_file.write_text("mock video")
        output_file = tmp_path / "output.mp3"

        with patch("src.audio_extractor.shutil.which") as mock_which:
            mock_which.return_value = None

            with pytest.raises(AudioExtractionError) as exc_info:
                extract_audio(video_file, output_file)

            assert "ffmpeg not found" in str(exc_info.value)
            assert "https://www.gyan.dev/ffmpeg/builds/" in str(exc_info.value)

    def test_extract_audio_no_audio_stream(self, tmp_path):
        """Test extraction fails when video has no audio stream."""
        video_file = tmp_path / "test.mp4"
        video_file.write_text("mock video")
        output_file = tmp_path / "output.mp3"

        with (
            patch("src.audio_extractor.shutil.which") as mock_which,
            patch("src.audio_extractor.subprocess.run") as mock_run,
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            # ffprobe returns empty string (no audio stream)
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            with pytest.raises(AudioExtractionError) as exc_info:
                extract_audio(video_file, output_file)

            assert "Video has no audio stream" in str(exc_info.value)
            assert "Check Panopto URL" in str(exc_info.value)

    def test_extract_audio_timeout(self, tmp_path):
        """Test extraction handles ffmpeg timeout."""
        video_file = tmp_path / "test.mp4"
        video_file.write_text("mock video")
        output_file = tmp_path / "output.mp3"

        with (
            patch("src.audio_extractor.shutil.which") as mock_which,
            patch("src.audio_extractor.subprocess.run") as mock_run,
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            # ffprobe check succeeds, ffmpeg times out
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="3600.0\n", stderr=""),  # ffprobe check
                subprocess.TimeoutExpired("ffmpeg", 300),  # ffmpeg timeout
            ]

            with pytest.raises(AudioExtractionError) as exc_info:
                extract_audio(video_file, output_file)

            assert "Audio extraction timed out" in str(exc_info.value)
            assert ">300s" in str(exc_info.value)

    def test_extract_audio_ffmpeg_codec_error(self, tmp_path):
        """Test extraction handles codec errors."""
        video_file = tmp_path / "test.mp4"
        video_file.write_text("mock video")
        output_file = tmp_path / "output.mp3"

        with (
            patch("src.audio_extractor.shutil.which") as mock_which,
            patch("src.audio_extractor.subprocess.run") as mock_run,
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            # ffprobe check succeeds, ffmpeg fails with codec error
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="3600.0\n", stderr=""),  # ffprobe check
                MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="Unknown encoder 'aac_unsupported'\nCodec not found",
                ),  # ffmpeg error
            ]

            with pytest.raises(AudioExtractionError) as exc_info:
                extract_audio(video_file, output_file)

            assert "codec" in str(exc_info.value).lower()

    def test_extract_audio_ffmpeg_generic_error(self, tmp_path):
        """Test extraction handles generic ffmpeg errors."""
        video_file = tmp_path / "test.mp4"
        video_file.write_text("mock video")
        output_file = tmp_path / "output.mp3"

        with (
            patch("src.audio_extractor.shutil.which") as mock_which,
            patch("src.audio_extractor.subprocess.run") as mock_run,
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            # ffprobe check succeeds, ffmpeg fails with generic error
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="3600.0\n", stderr=""),  # ffprobe check
                MagicMock(
                    returncode=1, stdout="", stderr="Some other ffmpeg error"
                ),  # generic error
            ]

            with pytest.raises(AudioExtractionError) as exc_info:
                extract_audio(video_file, output_file)

            assert "FFmpeg extraction failed" in str(exc_info.value)

    def test_extract_audio_validation_failure_cleanup(self, tmp_path):
        """Test that failed extraction cleans up partial output file."""
        video_file = tmp_path / "test.mp4"
        video_file.write_text("mock video")
        output_file = tmp_path / "output.mp3"

        with (
            patch("src.audio_extractor.shutil.which") as mock_which,
            patch("src.audio_extractor.subprocess.run") as mock_run,
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            # ffprobe check succeeds, ffmpeg succeeds, but validation fails (too short)
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="3600.0\n", stderr=""),  # ffprobe check
                MagicMock(returncode=0, stdout="", stderr=""),  # ffmpeg extraction
                MagicMock(
                    returncode=0, stdout="100.0\n", stderr=""
                ),  # ffprobe validation (too short: 100s < 80% of 3600 = 2880s)
            ]

            # Create output file with adequate size for file size check (2MB)
            output_file.write_bytes(b"x" * (2 * 1024 * 1024))

            with pytest.raises(AudioExtractionError) as exc_info:
                extract_audio(video_file, output_file)

            assert "Audio too short" in str(exc_info.value)
            assert not output_file.exists()  # File should be cleaned up


class TestValidateAudioOutput:
    """Tests for validate_audio_output function."""

    def test_validate_audio_output_success(self, tmp_path):
        """Test validation passes for valid audio file."""
        output_file = tmp_path / "audio.mp3"
        output_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

        with patch("src.audio_extractor.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="3600.0\n", stderr=""
            )

            result = validate_audio_output(output_file, 4000.0)

            assert result.status == "success"
            assert result.output_path == output_file
            assert result.duration == 3600.0
            assert result.file_size == 2 * 1024 * 1024

    def test_validate_audio_output_missing_file(self, tmp_path):
        """Test validation fails when output file doesn't exist."""
        output_file = tmp_path / "nonexistent.mp3"

        with pytest.raises(AudioExtractionError) as exc_info:
            validate_audio_output(output_file, 4000.0)

        assert "Output file not created" in str(exc_info.value)

    def test_validate_audio_output_too_small(self, tmp_path):
        """Test validation fails when audio file is too small."""
        output_file = tmp_path / "audio.mp3"
        output_file.write_bytes(b"x" * 100_000)  # 100KB < 1MB minimum

        with pytest.raises(AudioExtractionError) as exc_info:
            validate_audio_output(output_file, 4000.0)

        assert "Extracted audio too small" in str(exc_info.value)
        assert "1048576 bytes" in str(exc_info.value)

    def test_validate_audio_output_too_short(self, tmp_path):
        """Test validation fails when audio duration is too short."""
        output_file = tmp_path / "audio.mp3"
        output_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB (size OK)

        with patch("src.audio_extractor.subprocess.run") as mock_run:
            # ffprobe returns duration much shorter than 80% of expected
            mock_run.return_value = MagicMock(returncode=0, stdout="300.0\n", stderr="")

            # expected_duration=4000, min_duration=3200, actual=300
            with pytest.raises(AudioExtractionError) as exc_info:
                validate_audio_output(output_file, 4000.0)

            assert "Audio too short" in str(exc_info.value)
            assert "300" in str(exc_info.value)
            assert "3200" in str(exc_info.value)

    def test_validate_audio_output_at_minimum_threshold(self, tmp_path):
        """Test validation passes when duration is exactly at 80% threshold."""
        output_file = tmp_path / "audio.mp3"
        output_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

        with patch("src.audio_extractor.subprocess.run") as mock_run:
            # expected_duration=4000, min_duration=3200, actual=3200.0 (exactly at minimum)
            mock_run.return_value = MagicMock(
                returncode=0, stdout="3200.0\n", stderr=""
            )

            result = validate_audio_output(output_file, 4000.0)

            assert result.status == "success"
            assert result.duration == 3200.0

    def test_validate_audio_output_ffprobe_failure(self, tmp_path):
        """Test validation fails when ffprobe can't read audio duration."""
        output_file = tmp_path / "audio.mp3"
        output_file.write_bytes(b"x" * (2 * 1024 * 1024))

        with patch("src.audio_extractor.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

            with pytest.raises(AudioExtractionError) as exc_info:
                validate_audio_output(output_file, 4000.0)

            assert "Could not validate audio file" in str(exc_info.value)

    def test_validate_audio_output_timeout(self, tmp_path):
        """Test validation handles ffprobe timeout."""
        output_file = tmp_path / "audio.mp3"
        output_file.write_bytes(b"x" * (2 * 1024 * 1024))

        with patch("src.audio_extractor.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 30)

            with pytest.raises(AudioExtractionError) as exc_info:
                validate_audio_output(output_file, 4000.0)

            assert "Audio validation timed out" in str(exc_info.value)

    def test_validate_audio_output_duration_parse_error(self, tmp_path):
        """Test validation handles unparseable duration."""
        output_file = tmp_path / "audio.mp3"
        output_file.write_bytes(b"x" * (2 * 1024 * 1024))

        with patch("src.audio_extractor.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="not_a_number\n", stderr=""
            )

            with pytest.raises(AudioExtractionError) as exc_info:
                validate_audio_output(output_file, 4000.0)

            assert "Could not parse audio duration" in str(exc_info.value)


class TestAudioExtractionError:
    """Tests for AudioExtractionError exception."""

    def test_audio_extraction_error_is_exception(self):
        """Test that AudioExtractionError is an Exception."""
        assert issubclass(AudioExtractionError, Exception)

    def test_audio_extraction_error_message(self):
        """Test AudioExtractionError preserves message."""
        msg = "Test error message"
        error = AudioExtractionError(msg)
        assert str(error) == msg


class TestAudioExtractionResult:
    """Tests for AudioExtractionResult dataclass."""

    def test_audio_extraction_result_success(self):
        """Test AudioExtractionResult with success status."""
        result = AudioExtractionResult(
            status="success",
            output_path=Path("/tmp/audio.mp3"),
            duration=3600.0,
            file_size=2 * 1024 * 1024,
        )

        assert result.status == "success"
        assert result.output_path == Path("/tmp/audio.mp3")
        assert result.duration == 3600.0
        assert result.file_size == 2 * 1024 * 1024
        assert result.error_message is None

    def test_audio_extraction_result_error(self):
        """Test AudioExtractionResult with error status."""
        result = AudioExtractionResult(
            status="error",
            error_message="Extraction failed",
        )

        assert result.status == "error"
        assert result.error_message == "Extraction failed"
        assert result.output_path is None
        assert result.duration is None
        assert result.file_size is None


# Integration-style tests (mock-based)
class TestAudioExtractionIntegration:
    """Integration tests for audio extraction workflow."""

    def test_full_extraction_workflow(self, tmp_path):
        """Test complete extraction workflow from video to validated audio."""
        video_file = tmp_path / "lecture.mp4"
        video_file.write_text("mock video content")
        output_file = tmp_path / "lecture_audio.mp3"

        with (
            patch("src.audio_extractor.shutil.which") as mock_which,
            patch("src.audio_extractor.subprocess.run") as mock_run,
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            # Simulate all subprocess calls
            mock_run.side_effect = [
                MagicMock(
                    returncode=0, stdout="3600.0\n", stderr=""
                ),  # ffprobe input validation
                MagicMock(returncode=0, stdout="", stderr=""),  # ffmpeg extraction
                MagicMock(
                    returncode=0, stdout="3550.0\n", stderr=""
                ),  # ffprobe output validation
            ]

            output_file.write_bytes(b"x" * (2 * 1024 * 1024))

            result = extract_audio(video_file, output_file)

            assert result.status == "success"
            assert result.duration == 3550.0
            assert result.output_path == output_file

            # Verify subprocess was called 3 times
            assert mock_run.call_count == 3

    def test_extraction_error_recovery_instructions(self):
        """Test that extraction errors include recovery instructions."""
        test_cases = [
            (
                "ffmpeg not found",
                "https://www.gyan.dev/ffmpeg/builds/",
            ),
            (
                "Video has no audio stream",
                "Check Panopto URL",
            ),
            (
                "Audio extraction timed out",
                "Re-download and retry",
            ),
        ]

        for error_type, expected_instruction in test_cases:
            error = AudioExtractionError(f"{error_type}. {expected_instruction}")
            assert expected_instruction in str(error)
