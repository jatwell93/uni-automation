#!/usr/bin/env python3
"""
Process a lecture that's already been downloaded - Multi-course version.

Usage:
    python process_lecture.py MIS271 1 lecture          # Process lecture
    python process_lecture.py MIS271 1 prac             # Process practical
    python process_lecture.py MIS271 1                  # Default to lecture
    python process_lecture.py --list                    # List all available sessions
    python process_lecture.py --stats                   # Show session statistics

Manual workflow:
    1. Download video using Panopto-Video-DL
    2. Save to: downloads/MIS271_week_01_lecture/week_01_lecture/video.mp4
    3. Export transcript and save to: downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt
    4. Run this script to verify files and prepare for note generation
"""

import logging
import sys
import argparse
from pathlib import Path

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

from src.course_manager import CourseManager
from src.config import load_config


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
            "📊": "[STATS]",
            "📋": "[LIST]",
        }
        symbol_text = fallback.get(symbol, "[*]")
        print(f"{symbol_text} {message}")


def show_available_sessions(course_manager: CourseManager):
    """Display all available sessions that have been downloaded."""
    available = course_manager.list_available_sessions()

    if not available:
        print_progress("📋", "No downloaded sessions found")
        print("\nTo get started:")
        print("1. Download a video using Panopto-Video-DL")
        print(
            "2. Save to: downloads/MIS<CODE>_week_XX_<lecture|prac>/week_XX_<lecture|prac>/video.mp4"
        )
        print("3. Run: python process_lecture.py MIS271 1 lecture")
        return

    print_progress("📋", "Available downloaded sessions:")
    print()

    for course_code, week, session_type in available:
        session = course_manager.get_course_session(course_code, week, session_type)
        print(f"  • {session.display_name}")

    print()


def show_statistics(course_manager: CourseManager):
    """Display statistics about available sessions."""
    stats = course_manager.get_session_stats()

    print_progress("📊", "Session Statistics")
    print()
    print(f"Total sessions downloaded: {stats['total_sessions']}")
    print()

    for course_code, course_stats in stats["by_course"].items():
        print(f"{course_code}:")
        print(f"  Total:   {course_stats['total']}")
        print(f"  Lectures: {course_stats['lectures']}")
        print(f"  Pracs:   {course_stats['pracs']}")

    print()


def process_session(course_code: str, week_number: int, session_type: str = "lecture"):
    """Process a single lecture/practical session."""

    # Initialize course manager
    course_manager = CourseManager(downloads_root="downloads")

    try:
        session = course_manager.get_course_session(
            course_code, week_number, session_type
        )
    except ValueError as e:
        print_progress("✗", str(e))
        return 1

    print_progress("🔧", f"Processing: {session.display_name}")
    print()

    # Get file paths
    session_dir = course_manager.get_session_path(
        course_code, week_number, session_type
    )
    video_path = course_manager.get_video_path(course_code, week_number, session_type)

    # Check if video exists
    print_progress("🔍", "Checking for video file...")
    if not video_path.exists():
        print_progress("✗", f"Video not found: {video_path}")
        print()
        print("Expected location:")
        print(f"  {video_path}")
        print()
        print("To fix:")
        print("1. Download the video using Panopto-Video-DL")
        print("2. Save it to the path above")
        print("3. Run this script again")
        return 1

    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    print_progress("✓", f"Found video: {video_path.name} ({file_size_mb:.1f}MB)")

    # Check for transcript
    print_progress("📄", "Checking for transcript...")
    transcript_path = course_manager.find_transcript(
        course_code, week_number, session_type
    )

    if transcript_path:
        print_progress("✓", f"Found transcript: {transcript_path.name}")
    else:
        print_progress("~", "Transcript not found (optional)")
        print("  To include transcript: Export from Panopto and save to:")
        print(f"  {session_dir}/transcript.txt  OR  {session_dir}/transcript.vtt")

    # Summary
    print()
    print_progress("✓", "Lecture files ready for processing")
    print()
    print("Files:")
    print(f"  Video:      {video_path.name} ({file_size_mb:.1f}MB)")
    if transcript_path:
        print(f"  Transcript: {transcript_path.name}")

    print()
    print("Next steps:")
    print("1. Files are ready for analysis")
    print("2. You can generate Feynman notes using the LLM pipeline")
    print()

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process manually downloaded Panopto lectures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python process_lecture.py MIS271 1              # Process week 1 lecture (default)
  python process_lecture.py MIS271 1 lecture      # Explicit lecture
  python process_lecture.py MIS271 1 prac         # Process week 1 practical
  python process_lecture.py --list                # Show available sessions
  python process_lecture.py --stats               # Show statistics
        """,
    )

    parser.add_argument(
        "course", nargs="?", help="Course code (e.g., MIS271, MIS999) or --list/--stats"
    )
    parser.add_argument("week", nargs="?", type=int, help="Week number (1-11)")
    parser.add_argument(
        "session",
        nargs="?",
        default="lecture",
        choices=["lecture", "prac"],
        help="Session type (default: lecture)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List all available downloaded sessions"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show statistics about downloaded sessions"
    )

    args = parser.parse_args()

    # Initialize course manager
    course_manager = CourseManager(downloads_root="downloads")

    # Handle special arguments
    if args.list or args.course == "--list":
        show_available_sessions(course_manager)
        return 0

    if args.stats or args.course == "--stats":
        show_statistics(course_manager)
        return 0

    # Check that course and week are provided
    if not args.course or not args.week:
        parser.print_help()
        return 1

    # Process the session
    return process_session(args.course, args.week, args.session)


if __name__ == "__main__":
    sys.exit(main())
