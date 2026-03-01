"""Audio extraction module for lecture videos using FFmpeg."""

import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional

from src.models import AudioExtractionResult, AudioExtractionError


logger = logging.getLogger(__name__)


def extract_audio(
    video_path: Path, output_path: Path, codec: str = "aac"
) -> AudioExtractionResult:
    """
    Extract audio from video file using ffmpeg.

    Args:
        video_path: Path to input video file (must exist, must be readable)
        output_path: Path to output audio file (parent dir must exist and be writable)
        codec: Audio codec (default "aac" for MP4 container)

    Returns:
        AudioExtractionResult with status, output_path, duration, file_size

    Raises:
        AudioExtractionError: If extraction fails (codec unsupported, ffmpeg not found, etc.)
    """
    # Input validation
    video_path = Path(video_path)
    output_path = Path(output_path)

    # Verify input file exists
    if not video_path.exists():
        raise AudioExtractionError(f"Input video file not found: {video_path}")

    if video_path.stat().st_size == 0:
        raise AudioExtractionError(f"Input video file is empty: {video_path}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if ffmpeg is available
    if not shutil.which("ffmpeg"):
        raise AudioExtractionError(
            "ffmpeg not found. Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/ and add to PATH"
        )

    # Check if ffprobe is available
    if not shutil.which("ffprobe"):
        raise AudioExtractionError(
            "ffprobe not found. Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/ and add to PATH"
        )

    # Validate input video has audio stream using ffprobe
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=duration",
                "-of",
                "csv=p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise AudioExtractionError(
                "Video has no audio stream. Check Panopto URL and re-download."
            )
        input_duration = float(result.stdout.strip())
    except subprocess.TimeoutExpired:
        raise AudioExtractionError("ffprobe check timed out. Video may be corrupted.")
    except ValueError:
        raise AudioExtractionError(
            "Could not determine video duration. Video may be corrupted."
        )

    # Extract audio using ffmpeg
    try:
        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vn",  # No video
            "-acodec",
            codec,
            "-q:a",
            "5",  # Quality 5 (higher = better)
            "-y",  # Overwrite output
            str(output_path),
        ]

        logger.info(f"Running ffmpeg: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.lower()
            if "codec" in error_msg or "encoder" in error_msg:
                raise AudioExtractionError(
                    f"Audio codec '{codec}' unsupported. Install ffmpeg with full codec support."
                )
            elif "no such file" in error_msg:
                raise AudioExtractionError(f"Input video not found: {video_path}")
            else:
                raise AudioExtractionError(
                    f"FFmpeg extraction failed: {result.stderr[:200]}"
                )

    except subprocess.TimeoutExpired:
        # Clean up partial output file
        if output_path.exists():
            output_path.unlink()
        raise AudioExtractionError(
            "Audio extraction timed out (>300s). Video may be corrupted. Re-download and retry."
        )

    # Validate output
    try:
        result = validate_audio_output(output_path, input_duration)
        return result
    except AudioExtractionError:
        # Clean up failed extraction
        if output_path.exists():
            output_path.unlink()
        raise


def validate_audio_output(
    output_path: Path, expected_duration: float
) -> AudioExtractionResult:
    """
    Validate extracted audio file for integrity.

    Checks:
    - File exists and is readable
    - File size ≥ 1MB (non-empty)
    - Duration ≥ 80% of expected (accounts for subtitle-only segments)
    - Audio stream exists (ffprobe check)

    Args:
        output_path: Path to extracted audio file
        expected_duration: Duration of original video (seconds)

    Returns:
        AudioExtractionResult with validation status

    Raises:
        AudioExtractionError: If any validation fails
    """
    output_path = Path(output_path)

    # File existence check
    if not output_path.exists():
        raise AudioExtractionError(
            "Output file not created. FFmpeg may have failed silently."
        )

    # File size check (minimum 1MB)
    file_size = output_path.stat().st_size
    min_file_size = 1_048_576  # 1MB

    if file_size < min_file_size:
        raise AudioExtractionError(
            f"Extracted audio too small ({file_size} bytes < {min_file_size} bytes). "
            "Extraction likely failed. Re-download video and retry."
        )

    # Duration check with ffprobe
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=duration",
                "-of",
                "csv=p=0",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0 or not result.stdout.strip():
            raise AudioExtractionError(
                "Could not validate audio file. Check ffmpeg installation."
            )

        actual_duration = float(result.stdout.strip())
        min_duration = expected_duration * 0.8

        if actual_duration < min_duration:
            raise AudioExtractionError(
                f"Audio too short ({actual_duration:.1f}s < {min_duration:.1f}s expected). "
                "Extraction likely failed. Re-download video and retry."
            )

        return AudioExtractionResult(
            status="success",
            output_path=output_path,
            duration=actual_duration,
            file_size=file_size,
        )

    except subprocess.TimeoutExpired:
        raise AudioExtractionError("Audio validation timed out. File may be corrupted.")
    except ValueError:
        raise AudioExtractionError(
            "Could not parse audio duration. File may be corrupted."
        )
