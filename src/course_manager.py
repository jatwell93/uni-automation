"""
Multi-course management for handling multiple units and sessions.

Provides utilities for:
- Managing folder structure for multiple courses
- Handling lecture and practical sessions
- Auto-generating course-specific configurations
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CourseSession:
    """Represents a course session (lecture or practical)."""

    course_code: str  # e.g., "MIS271"
    course_name: str  # e.g., "Business Intelligence and Data Warehousing"
    week_number: int  # 1-11
    session_type: str  # "lecture" or "prac"
    obsidian_folder: str  # e.g., "MIS271_BI_DW"

    @property
    def folder_name(self) -> str:
        """Generate folder name for this session."""
        return f"{self.course_code}_week_{self.week_number:02d}_{self.session_type}"

    @property
    def subfolder(self) -> str:
        """Generate subfolder name (week_XX_lecture or week_XX_prac)."""
        return f"week_{self.week_number:02d}_{self.session_type}"

    @property
    def display_name(self) -> str:
        """Human-readable name for this session."""
        session = "Lecture" if self.session_type == "lecture" else "Practical"
        return f"{self.course_code} - {session} (Week {self.week_number})"


class CourseManager:
    """Manages multi-course lecture structure and file organization."""

    # Define all courses for the trimester
    COURSES = {
        "MIS271": {
            "name": "Business Intelligence and Data Warehousing",
            "obsidian_folder": "MIS271_BI_DW",
            "weeks": 11,
        },
        "MIS999": {
            "name": "Artificial Intelligence for Business",
            "obsidian_folder": "MIS999_AI_Business",
            "weeks": 11,
        },
    }

    def __init__(self, downloads_root: str = "downloads"):
        """Initialize course manager."""
        self.downloads_root = Path(downloads_root)
        self.downloads_root.mkdir(parents=True, exist_ok=True)

    def get_course_session(
        self, course_code: str, week_number: int, session_type: str = "lecture"
    ) -> CourseSession:
        """
        Get or create a CourseSession object.

        Args:
            course_code: Course code (e.g., "MIS271")
            week_number: Week number (1-11)
            session_type: "lecture" or "prac"

        Returns:
            CourseSession object

        Raises:
            ValueError: If course code or parameters are invalid
        """
        if course_code not in self.COURSES:
            raise ValueError(
                f"Unknown course code: {course_code}. "
                f"Available: {', '.join(self.COURSES.keys())}"
            )

        course_info = self.COURSES[course_code]

        if not (1 <= week_number <= course_info["weeks"]):
            raise ValueError(
                f"Invalid week number: {week_number}. "
                f"Course {course_code} has {course_info['weeks']} weeks"
            )

        if session_type not in ("lecture", "prac"):
            raise ValueError(
                f"Session type must be 'lecture' or 'prac', got: {session_type}"
            )

        return CourseSession(
            course_code=course_code,
            course_name=course_info["name"],
            week_number=week_number,
            session_type=session_type,
            obsidian_folder=course_info["obsidian_folder"],
        )

    def get_session_path(
        self, course_code: str, week_number: int, session_type: str = "lecture"
    ) -> Path:
        """
        Get the file path for a course session.

        Returns:
            Path to session folder (e.g., downloads/MIS271_week_01_lecture/week_01_lecture/)
        """
        session = self.get_course_session(course_code, week_number, session_type)
        session_dir = self.downloads_root / session.folder_name / session.subfolder
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def get_video_path(
        self, course_code: str, week_number: int, session_type: str = "lecture"
    ) -> Path:
        """Get the expected video file path for a session."""
        return (
            self.get_session_path(course_code, week_number, session_type) / "video.mp4"
        )

    def get_transcript_path(
        self,
        course_code: str,
        week_number: int,
        session_type: str = "lecture",
        format_type: str = "txt",
    ) -> Path:
        """
        Get the expected transcript file path for a session.

        Args:
            format_type: "txt", "vtt", or "auto" (looks for either)
        """
        session_dir = self.get_session_path(course_code, week_number, session_type)

        if format_type == "auto":
            # Check for .txt first, then .vtt
            txt_path = session_dir / "transcript.txt"
            if txt_path.exists():
                return txt_path
            return session_dir / "transcript.vtt"

        return session_dir / f"transcript.{format_type}"

    def find_transcript(
        self, course_code: str, week_number: int, session_type: str = "lecture"
    ) -> Optional[Path]:
        """
        Find transcript file in either .txt or .vtt format.

        Returns:
            Path to transcript if found, None otherwise
        """
        session_dir = self.get_session_path(course_code, week_number, session_type)

        for ext in ["txt", "vtt"]:
            transcript_path = session_dir / f"transcript.{ext}"
            if transcript_path.exists():
                return transcript_path

        return None

    def list_available_sessions(self) -> list:
        """
        List all sessions that have video files available.

        Returns:
            List of (course_code, week_number, session_type) tuples
        """
        available = []

        for course_code, course_info in self.COURSES.items():
            for week in range(1, course_info["weeks"] + 1):
                for session_type in ["lecture", "prac"]:
                    video_path = self.get_video_path(course_code, week, session_type)
                    if video_path.exists():
                        available.append((course_code, week, session_type))

        return sorted(available)

    def get_all_sessions_for_course(self, course_code: str) -> list:
        """Get all available sessions for a specific course."""
        return [
            (cc, w, st)
            for cc, w, st in self.list_available_sessions()
            if cc == course_code
        ]

    def get_session_stats(self) -> dict:
        """Get statistics about available sessions."""
        available = self.list_available_sessions()

        stats = {
            "total_sessions": len(available),
            "by_course": {},
        }

        for course_code in self.COURSES.keys():
            course_sessions = [s for s in available if s[0] == course_code]
            stats["by_course"][course_code] = {
                "total": len(course_sessions),
                "lectures": len([s for s in course_sessions if s[2] == "lecture"]),
                "pracs": len([s for s in course_sessions if s[2] == "prac"]),
            }

        return stats
