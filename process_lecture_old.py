#!/usr/bin/env python3
"""
Process a lecture that's already been downloaded.

Usage:
    python process_lecture.py config/week_01.yaml

This script assumes you've already manually:
1. Downloaded the video and saved it to: downloads/MIS272_week_01/week_01/video.mp4
2. Exported the transcript and saved it to: downloads/MIS272_week_01/week_01/transcript.vtt

It will then generate Feynman-technique notes and save them to Obsidian.
"""

import logging
import sys
from pathlib import Path

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

from src.config import load_config
from src.validator import validate_video


def print_progress(symbol: str, message: str):
    """Print progress message with emoji indicator."""
    try:
        print(f"{symbol} {message}")
    except UnicodeEncodeError:
        # Fallback for Windows console that doesn't support emoji
        fallback = {
            "🔧": "[*]",
            "✓": "[+]",
            "📄": "[FILE]",
            "🔍": "[CHECK]",
            "📝": "[NOTES]",
        }
        symbol_text = fallback.get(symbol, "[*]")
        print(f"{symbol_text} {message}")


def main():
    """Process a lecture that's already been downloaded."""
    if len(sys.argv) < 2:
        print("Usage: python process_lecture.py config/week_01.yaml")
        return 1

    config_file = sys.argv[1]

    # Load configuration
    try:
        print_progress("🔧", f"Loading config from {config_file}...")
        config = load_config(config_file)
        print_progress("✓", "Config validated")
    except FileNotFoundError:
        print_progress("✗", f"Config file not found: {config_file}")
        return 1
    except Exception as e:
        print_progress("✗", f"Config validation failed: {e}")
        return 1

    # Setup output directory
    output_dir = (
        Path(config.paths.output_dir) / f"week_{config.metadata.week_number:02d}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    video_output = output_dir / "video.mp4"
    transcript_output = output_dir / "transcript.vtt"

    # Check if video exists
    print_progress("🔍", "Checking for video file...")
    if not video_output.exists():
        print_progress("✗", f"Video not found: {video_output}")
        print("  Please download the video manually and save it to the path above")
        return 1
    print_progress("✓", f"Found video: {video_output}")

    # Validate video
    print_progress("🔍", "Validating video...")
    try:
        validation_result = validate_video(
            video_path=video_output,
            min_size_mb=10,  # Lower threshold for manual downloads
            min_duration_sec=30,
        )

        if not validation_result.success:
            print_progress("✗", validation_result.error)
            logger.error(f"Validation failed: {validation_result.error}")
            # For manual downloads, FFmpeg is optional - just warn and proceed
            if "FFmpeg" in validation_result.error:
                print_progress(
                    "~", "FFmpeg not installed - skipping detailed validation"
                )
                print(
                    "  To validate video: Install FFmpeg from https://gyan.dev/ffmpeg/builds/"
                )
                print(
                    "  Proceeding anyway since validation is optional for manual downloads"
                )
            else:
                return 1

        if validation_result.success:
            print_progress("✓", validation_result.message)
    except Exception as e:
        error_str = str(e)
        if "FFmpeg" in error_str:
            print_progress("~", "FFmpeg not installed - skipping detailed validation")
            print(
                "  To validate video: Install FFmpeg from https://gyan.dev/ffmpeg/builds/"
            )
            print(
                "  Proceeding anyway since validation is optional for manual downloads"
            )
            logger.debug(f"Validation skipped (FFmpeg not available): {e}")
        else:
            print_progress("✗", f"Validation error: {e}")
            print("  Recovery: Check that ffprobe is installed (part of ffmpeg)")
            logger.error(f"Validation error: {e}", exc_info=True)
            return 1

    # Check for transcript (supports both .vtt and .txt formats)
    print_progress("📄", "Checking for transcript...")
    transcript_txt = output_dir / "transcript.txt"

    if transcript_output.exists():
        print_progress("✓", f"Found transcript: {transcript_output}")
    elif transcript_txt.exists():
        print_progress("✓", f"Found transcript: {transcript_txt}")
        transcript_output = transcript_txt  # Use .txt version
    else:
        print_progress("~", "Transcript not found (optional)")
        print("  To include transcript: Export from Panopto and save to either:")
        print(f"  {transcript_output} (VTT format)")
        print(f"  {transcript_txt} (TXT format)")

    # Summary
    print()
    print_progress("✓", "Lecture files ready for processing")
    print("Next steps:")
    print("1. Video is ready for analysis")
    print("2. Transcript is ready (if provided)")
    print("3. You can now generate Feynman notes using the LLM pipeline")
    print()
    try:
        print(f"Video: {video_output.relative_to(Path.cwd())}")
    except ValueError:
        print(f"Video: {video_output}")

    if transcript_output.exists():
        try:
            print(f"Transcript: {transcript_output.relative_to(Path.cwd())}")
        except ValueError:
            print(f"Transcript: {transcript_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
