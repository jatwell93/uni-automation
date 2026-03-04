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


def create_session_folders(
    course_manager: CourseManager, course_code: str, week_number: int
):
    """Create folders for both lecture and practical sessions for a week."""

    try:
        session_manager = course_manager.get_course_session(
            course_code, week_number, "lecture"
        )
    except ValueError as e:
        print_progress("✗", str(e))
        return 1

    print_progress("🔧", f"Creating folders for {course_code} Week {week_number}")
    print()

    created_folders = []

    for session_type in ["lecture", "prac"]:
        session_dir = course_manager.get_session_path(
            course_code, week_number, session_type
        )
        session = course_manager.get_course_session(
            course_code, week_number, session_type
        )

        created_folders.append(session_dir)
        print_progress("✓", f"Created: {session_dir}")

    print()
    print_progress("✓", "Folders created successfully")
    print()
    print("Next steps:")
    print("1. Download video using Panopto-Video-DL")
    print("2. Save to one of the folders created above as 'video.mp4'")
    print("3. Export transcript and save as 'transcript.txt' (optional)")
    print(
        "4. Run: python process_lecture.py --course", course_code, "--week", week_number
    )
    print()

    return 0


def create_all_course_folders(course_manager: CourseManager, course_code: str):
    """Create all folders for a course (11 weeks × 2 sessions)."""

    # Validate course code format
    if not course_manager.is_valid_course_code(course_code):
        print_progress("✗", f"Invalid course code format: {course_code}")
        print("Course codes must be 3 letters + 3 digits (e.g., MIS271, CHM101)")
        return 1

    try:
        course_info = course_manager._get_course_info(course_code)
    except ValueError as e:
        print_progress("✗", str(e))
        return 1

    weeks = course_info["weeks"]

    print_progress(
        "🔧", f"Creating all folders for {course_code} ({weeks} weeks × 2 sessions)"
    )
    print()

    total_created = 0

    for week_num in range(1, weeks + 1):
        for session_type in ["lecture", "prac"]:
            session_dir = course_manager.get_session_path(
                course_code, week_num, session_type
            )
            total_created += 1

    print_progress(
        "✓", f"Created {total_created} folder structures ({weeks} weeks × 2 sessions)"
    )
    print()
    print("Folder structure:")
    print(f"  downloads/{course_code}_week_01_lecture/week_01_lecture/")
    print(f"  downloads/{course_code}_week_01_prac/week_01_prac/")
    print(f"  downloads/{course_code}_week_02_lecture/week_02_lecture/")
    print(f"  ... (continues for all {weeks} weeks)")
    print()
    print("Next steps:")
    print("1. Download videos using Panopto-Video-DL")
    print("2. Save to corresponding folders as 'video.mp4'")
    print("3. Export transcripts and save as 'transcript.txt' (optional)")
    print("4. Use 'python process_lecture.py --stats' to track progress")
    print()

    return 0


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
Examples (Positional arguments):
  python process_lecture.py MIS271 1              # Process week 1 lecture (default)
  python process_lecture.py MIS271 1 lecture      # Explicit lecture
  python process_lecture.py MIS271 1 prac         # Process week 1 practical

Examples (Named arguments - recommended):
  python process_lecture.py --course MIS271 --week 1                # Lecture (default)
  python process_lecture.py --course MIS271 --week 1 --session lecture  # Explicit
  python process_lecture.py --course MIS271 --week 1 --session prac     # Practical

Examples (Other commands):
  python process_lecture.py --list                # Show available sessions
  python process_lecture.py --stats               # Show statistics
  python process_lecture.py --create MIS271 1     # Create folders for week 1
  python process_lecture.py --create-all MIS271   # Create all folders for course
        """,
    )

    # Positional arguments (for backwards compatibility)
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

    # Named arguments (recommended)
    parser.add_argument(
        "--course", dest="course_flag", help="Course code (e.g., MIS271, MIS999)"
    )
    parser.add_argument("--week", type=int, dest="week_flag", help="Week number (1-11)")
    parser.add_argument(
        "--session",
        choices=["lecture", "prac"],
        default="lecture",
        dest="session_flag",
        help="Session type (default: lecture)",
    )

    # Special commands
    parser.add_argument(
        "--list", action="store_true", help="List all available downloaded sessions"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show statistics about downloaded sessions"
    )
    parser.add_argument(
        "--create",
        nargs=2,
        metavar=("COURSE", "WEEK"),
        help="Create folders for a specific session (e.g., --create MIS271 1)",
    )
    parser.add_argument(
        "--create-all",
        metavar="COURSE",
        help="Create all folders for a course (11 weeks × 2 sessions)",
    )

    args = parser.parse_args()

    # Initialize course manager
    course_manager = CourseManager(downloads_root="downloads")

    # Handle special commands
    if args.list or args.course == "--list":
        show_available_sessions(course_manager)
        return 0

    if args.stats or args.course == "--stats":
        show_statistics(course_manager)
        return 0

    if args.create:
        course_code, week_str = args.create
        try:
            week_num = int(week_str)
            return create_session_folders(course_manager, course_code, week_num)
        except (ValueError, IndexError):
            print_progress("✗", f"Invalid arguments for --create: {args.create}")
            return 1

    if args.create_all:
        return create_all_course_folders(course_manager, args.create_all)

    # Determine which arguments were provided
    if args.course_flag and args.week_flag:
        # Named arguments provided
        course_code = args.course_flag
        week_num = args.week_flag
        session_type = args.session_flag
    elif args.course and args.week:
        # Positional arguments provided
        course_code = args.course
        week_num = args.week
        session_type = args.session
    else:
        parser.print_help()
        return 1

    # Process the session
    return process_session(course_code, week_num, session_type)


if __name__ == "__main__":
    sys.exit(main())
