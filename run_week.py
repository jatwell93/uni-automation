#!/usr/bin/env python3
"""
Main CLI entry point for processing a weekly lecture.

Usage:
    python run_week.py config/week_05.yaml
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

from src.config import load_config
from src.auth import load_cookies, validate_session
from src.downloader import (
    download_video,
    download_transcript,
    extract_session_id,
    extract_base_url,
)
from src.validator import validate_video


def setup_logging(log_file: Path):
    """Configure file logging."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Add to root logger
    logging.getLogger().addHandler(file_handler)
    logger.debug(f"Logging to {log_file}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python run_week.py <config_file>")
        print("Example: python run_week.py config/week_05.yaml")
        sys.exit(1)

    config_file = sys.argv[1]

    # Load configuration
    try:
        print(f"🔧 Loading config from {config_file}...")
        config = load_config(config_file)
    except Exception as e:
        print(f"✗ Config validation failed: {e}")
        logger.error(f"Config validation failed: {e}", exc_info=True)
        sys.exit(1)

    # Setup logging with file
    log_dir = Path(".planning/logs")
    log_file = log_dir / f"week_{config.metadata.week_number:02d}.log"
    setup_logging(log_file)

    # Load cookies
    try:
        logger.info(f"Loading cookies from {config.paths.cookie_file}...")
        cookies = load_cookies(config.paths.cookie_file)
    except Exception as e:
        print(f"✗ Failed to load cookies: {e}")
        logger.error(f"Failed to load cookies: {e}", exc_info=True)
        sys.exit(1)

    # Validate session
    print(f"🔐 Testing Panopto authentication...")
    base_url = extract_base_url(config.lecture.url)
    session_result = validate_session(cookies, base_url)

    if not session_result.valid:
        print(f"✗ {session_result.message}")
        logger.error(f"Session validation failed: {session_result.message}")
        sys.exit(1)

    print(f"✓ {session_result.message}")

    # Download video
    output_dir = (
        Path(config.paths.output_dir) / f"week_{config.metadata.week_number:02d}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    video_output = output_dir / "video.mp4"

    print(f"📥 Downloading video...")
    download_result = download_video(
        video_url=config.lecture.url,
        output_path=video_output,
        cookies=cookies,
        timeout=300,
    )

    if not download_result.success:
        print(f"✗ {download_result.error}")
        logger.error(f"Download failed: {download_result.error}")
        sys.exit(1)

    print(f"✓ {download_result.message}")

    # Validate video
    print(f"🔍 Validating video...")
    validation_result = validate_video(
        video_path=video_output,
        min_size_mb=100,
        min_duration_sec=60,
    )

    if not validation_result.success:
        print(f"✗ {validation_result.error}")
        logger.error(f"Validation failed: {validation_result.error}")
        # Delete video on validation failure
        try:
            video_output.unlink()
            logger.info(f"Deleted invalid video: {video_output}")
        except Exception as e:
            logger.warning(f"Failed to delete invalid video: {e}")
        sys.exit(1)

    print(f"✓ {validation_result.message}")

    # Download transcript (optional)
    print(f"📄 Downloading transcript...")
    transcript_output = output_dir / "transcript.vtt"
    session_id = extract_session_id(config.lecture.url)

    if session_id:
        transcript_result = download_transcript(
            session_id=session_id,
            output_path=transcript_output,
            cookies=cookies,
            panopto_base_url=base_url,
        )

        if transcript_result.success:
            print(f"✓ {transcript_result.message}")
        else:
            print(f"⚠ {transcript_result.message}")
    else:
        print(f"⚠ Could not extract session ID from URL; skipping transcript")
        logger.warning("Could not extract session ID from URL; skipping transcript")

    # Success summary
    print(f"\n✓ Phase 1 complete")
    print(f"Files:")
    print(
        f"- {video_output.relative_to(Path.cwd())} ({download_result.file_size / (1024 * 1024):.1f}MB)"
    )

    if transcript_output.exists():
        print(f"- {transcript_output.relative_to(Path.cwd())}")

    print(f"✓ Logs: {log_file.relative_to(Path.cwd())}")

    logger.info("Phase 1 complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
