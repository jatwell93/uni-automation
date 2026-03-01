"""Video validation using ffprobe."""

import logging
import shutil
import subprocess
import os
from pathlib import Path
from typing import Optional

from src.models import ValidationResult

logger = logging.getLogger(__name__)


def validate_video(
    video_path: str | Path,
    min_size_mb: int = 100,
    min_duration_sec: float = 60,
) -> ValidationResult:
    """
    Validate video file using ffprobe.

    Checks:
    - File exists and is readable
    - Duration >= min_duration_sec (default 60s)
    - File size >= min_size_mb (default 100 MB)
    - File is a valid video (ffprobe can extract metadata)

    Args:
        video_path: Path to video file
        min_size_mb: Minimum file size in MB (default 100)
        min_duration_sec: Minimum duration in seconds (default 60)

    Returns:
        ValidationResult with success status and metadata
    """
    video_path = Path(video_path)

    try:
        # Check if file exists
        if not video_path.exists():
            error_msg = f"Video file not found: {video_path}"
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )

        # Check if ffprobe is installed
        ffprobe_path = shutil.which("ffprobe")
        if not ffprobe_path:
            # Check FFMPEG_HOME environment variable as fallback
            ffmpeg_home = os.environ.get("FFMPEG_HOME")
            if ffmpeg_home:
                ffprobe_path = Path(ffmpeg_home) / (
                    "ffprobe.exe" if os.name == "nt" else "ffprobe"
                )
                if not ffprobe_path.exists():
                    ffprobe_path = None

        if not ffprobe_path:
            error_msg = (
                "FFmpeg not installed.\n"
                "Download from: https://gyan.dev/ffmpeg/builds/\n"
                "After install, add to PATH or set FFMPEG_HOME env var"
            )
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )

        logger.info(f"Validating video {video_path}...")

        # Run ffprobe to extract metadata
        # Command: ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1:nokey=1:ch=, <video_path>
        try:
            result = subprocess.run(
                [
                    str(ffprobe_path),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration,size",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1:ch=,",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            error_msg = "Video validation timeout. File may be very large or corrupted. Try again or validate manually."
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )

        if result.returncode != 0:
            error_msg = f"ffmpeg error: {result.stderr.strip()}. File may be corrupted or unsupported format."
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )

        # Parse ffprobe output
        # Output format (with nokey=1):
        # duration_in_seconds
        # size_in_bytes
        lines = result.stdout.strip().split("\n")

        duration_seconds = None
        file_size_bytes = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                # First non-empty line should be duration
                if duration_seconds is None:
                    duration_seconds = float(line)
                # Second non-empty line should be size
                elif file_size_bytes is None:
                    file_size_bytes = int(float(line))
            except ValueError:
                # Skip lines that can't be parsed
                pass

        if duration_seconds is None or file_size_bytes is None:
            error_msg = (
                "Could not parse ffprobe output. File format may be unsupported."
            )
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )

        # Validate thresholds
        file_size_mb = file_size_bytes / (1024 * 1024)

        if duration_seconds < min_duration_sec:
            error_msg = f"Video duration {duration_seconds:.1f}s is below minimum {min_duration_sec}s. File may be corrupted."
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                duration_seconds=duration_seconds,
                file_size_bytes=file_size_bytes,
                error=error_msg,
                message=error_msg,
            )

        if file_size_mb < min_size_mb:
            error_msg = f"File size {file_size_mb:.1f}MB is below minimum {min_size_mb}MB. Download may have been interrupted."
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                duration_seconds=duration_seconds,
                file_size_bytes=file_size_bytes,
                error=error_msg,
                message=error_msg,
            )

        # Extract codec name for informational purposes
        codec_result = subprocess.run(
            [
                str(ffprobe_path),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        codec_name = None
        if codec_result.returncode == 0:
            codec_name = codec_result.stdout.strip()

        success_msg = f"✓ Video valid: {duration_seconds:.0f}s, {file_size_mb:.1f}MB"
        if codec_name:
            success_msg += f", {codec_name}"

        logger.info(success_msg)

        return ValidationResult(
            success=True,
            duration_seconds=duration_seconds,
            file_size_bytes=file_size_bytes,
            codec_name=codec_name,
            message=success_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during validation: {str(e)}"
        logger.error(error_msg)
        return ValidationResult(
            success=False,
            error=error_msg,
            message=error_msg,
        )
