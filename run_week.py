#!/usr/bin/env python3
"""
Main CLI entry point for processing a weekly lecture.

Usage:
    python run_week.py config/week_05.yaml

Features:
- Comprehensive error handling with recovery instructions
- Progress output with emoji indicators
- Detailed logging to file with timestamps
- Exit codes: 0 on success, 1 on error
"""

import logging
import sys
from pathlib import Path

# Configure basic logging (before imports)
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
    """Configure file logging with both file and console output."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)

    # Add to root logger
    logging.getLogger().addHandler(file_handler)
    logger.debug(f"Logging to {log_file}")


def print_progress(symbol: str, message: str):
    """Print progress message with emoji indicator."""
    try:
        print(f"{symbol} {message}")
    except UnicodeEncodeError:
        # Fallback for Windows console that doesn't support emoji
        fallback = {
            "🔧": "[*]",
            "✓": "[+]",
            "🔐": "[AUTH]",
            "📥": "[DL]",
            "🔍": "[CHECK]",
            "📄": "[TRANSCRIPT]",
        }
        symbol_text = fallback.get(symbol, "[*]")
        print(f"{symbol_text} {message}")


def main():
    """Main entry point with comprehensive error handling."""
    if len(sys.argv) < 2:
        print("Usage: python run_week.py <config_file>")
        print("Example: python run_week.py config/week_05.yaml")
        return 1

    config_file = sys.argv[1]

    # Load configuration
    try:
        print_progress("🔧", f"Loading config from {config_file}...")
        config = load_config(config_file)
        print_progress("✓", "Config validated")
    except FileNotFoundError as e:
        print_progress("✗", f"Config file not found: {config_file}")
        print("  Recovery: Check the file path and try again")
        logger.error(f"Config file not found: {config_file}", exc_info=True)
        return 1
    except Exception as e:
        print_progress("✗", f"Config validation failed: {e}")
        print(
            "  Recovery: Check YAML syntax and required fields (lecture.url, paths.cookie_file, paths.output_dir)"
        )
        logger.error(f"Config validation failed: {e}", exc_info=True)
        return 1

    # Setup logging with file
    log_dir = Path(".planning/logs")
    log_file = log_dir / f"week_{config.metadata.week_number:02d}.log"
    setup_logging(log_file)

    # Load cookies
    try:
        logger.info(f"Loading cookies from {config.paths.cookie_file}...")
        cookies = load_cookies(config.paths.cookie_file)
        logger.info("Cookies loaded successfully")
    except FileNotFoundError:
        print_progress("✗", f"Cookie file not found: {config.paths.cookie_file}")
        print(
            "  Recovery: Export cookies from browser (F12 → Storage → Cookies) and save to the specified path"
        )
        logger.error(f"Cookie file not found: {config.paths.cookie_file}")
        return 1
    except Exception as e:
        print_progress("✗", f"Failed to load cookies: {e}")
        print("  Recovery: Ensure cookie file is valid JSON or browser export format")
        logger.error(f"Failed to load cookies: {e}", exc_info=True)
        return 1

    # Validate session
    print_progress("🔐", "Testing Panopto authentication...")
    try:
        base_url = extract_base_url(config.lecture.url)
        session_result = validate_session(cookies, base_url)

        if not session_result.success:
            print_progress("✗", session_result.message)
            print("  Recovery: Refresh cookies from browser and try again")
            logger.error(f"Session validation failed: {session_result.message}")
            return 1

        print_progress("✓", session_result.message)
        logger.info(f"Session validated: {session_result.message}")
    except Exception as e:
        print_progress("✗", f"Authentication error: {e}")
        print("  Recovery: Check that Panopto is accessible and cookies are valid")
        logger.error(f"Authentication error: {e}", exc_info=True)
        return 1

    # Download video
    output_dir = (
        Path(config.paths.output_dir) / f"week_{config.metadata.week_number:02d}"
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print_progress("✗", f"Cannot create output directory: {output_dir}")
        print(f"  Recovery: Ensure parent directory exists and is writable")
        logger.error(f"Cannot create output directory: {e}", exc_info=True)
        return 1

    video_output = output_dir / "video.mp4"

    print_progress("📥", "Downloading video...")
    try:
        download_result = download_video(
            video_url=config.lecture.url,
            output_path=video_output,
            cookies=cookies,
            timeout=300,
        )

        if not download_result.success:
            print_progress("✗", download_result.error)
            print(
                "  Recovery: Check internet connection, URL validity, and cookie freshness"
            )
            logger.error(f"Download failed: {download_result.error}")
            return 1

        print_progress("✓", download_result.message)
        logger.info(f"Video downloaded: {download_result.message}")
    except Exception as e:
        print_progress("✗", f"Download error: {e}")
        print("  Recovery: Check network connection and available disk space")
        logger.error(f"Download error: {e}", exc_info=True)
        # Cleanup partial file
        try:
            if video_output.exists():
                video_output.unlink()
                logger.info(f"Cleaned up partial file: {video_output}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up partial file: {cleanup_error}")
        return 1

    # Validate video
    print_progress("🔍", "Validating video...")
    try:
        validation_result = validate_video(
            video_path=video_output,
            min_size_mb=100,
            min_duration_sec=60,
        )

        if not validation_result.success:
            print_progress("✗", validation_result.error)
            print(
                "  Recovery: Download may have been interrupted. Try again with fresh cookies."
            )
            logger.error(f"Validation failed: {validation_result.error}")
            # Delete invalid video
            try:
                video_output.unlink()
                logger.info(f"Deleted invalid video: {video_output}")
            except Exception as e:
                logger.warning(f"Failed to delete invalid video: {e}")
            return 1

        print_progress("✓", validation_result.message)
        logger.info(f"Video validated: {validation_result.message}")
    except Exception as e:
        print_progress("✗", f"Validation error: {e}")
        print("  Recovery: Check that ffprobe is installed (part of ffmpeg)")
        logger.error(f"Validation error: {e}", exc_info=True)
        return 1

    # Download transcript (optional)
    print_progress("📄", "Downloading transcript...")
    transcript_output = output_dir / "transcript.vtt"
    session_id = extract_session_id(config.lecture.url)

    if session_id:
        try:
            transcript_result = download_transcript(
                session_id=session_id,
                output_path=transcript_output,
                cookies=cookies,
                panopto_base_url=base_url,
            )

            if transcript_result.success:
                print_progress("✓", transcript_result.message)
                logger.info(f"Transcript downloaded: {transcript_result.message}")
            else:
                print_progress("~", transcript_result.message)
                logger.warning(
                    f"Transcript download skipped: {transcript_result.message}"
                )
        except Exception as e:
            print_progress("~", f"Transcript download failed: {e}")
            logger.warning(f"Transcript download error: {e}")
            # Don't fail pipeline if transcript fails
    else:
        print_progress(
            "~", "Could not extract session ID from URL; skipping transcript"
        )
        logger.warning("Could not extract session ID from URL; skipping transcript")

    # Success summary
    print()
    print_progress("✓", "Phase 1 complete")
    print("Files:")
    try:
        file_size_mb = download_result.file_size / (1024 * 1024)
        print(f"  - {video_output.relative_to(Path.cwd())} ({file_size_mb:.1f}MB)")
    except:
        print(f"  - {video_output.relative_to(Path.cwd())}")

    if transcript_output.exists():
        print(f"  - {transcript_output.relative_to(Path.cwd())}")

    print(f"✓ Logs: {log_file.relative_to(Path.cwd())}")
    logger.info("Phase 1 complete - success")
    return 0


if __name__ == "__main__":
    sys.exit(main())
