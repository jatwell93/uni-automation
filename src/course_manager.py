"""
Multi-course management for handling multiple units and sessions.

Provides utilities for:
- Managing folder structure for multiple courses
- Handling lecture and practical sessions
- Auto-generating course-specific configurations
- Dynamic course code validation (e.g., MIS271, MIS999, CHM101, etc.)
"""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple, Dict
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

    # Define known courses with custom metadata
    # Add entries here for courses with non-standard week counts or special metadata
    KNOWN_COURSES: Dict[str, dict] = {
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

    # Pattern for valid Deakin course codes (3 letters + 3 digits)
    # Examples: MIS271, CHM101, ENG202, BIO333, etc.
    COURSE_CODE_PATTERN = re.compile(r"^[A-Z]{3}\d{3}$")

    # Default values for unknown courses
    DEFAULT_WEEKS = 11
    DEFAULT_OBSIDIAN_FOLDER_TEMPLATE = "{course_code}"

    def __init__(self, downloads_root: str = "downloads"):
        """Initialize course manager."""
        self.downloads_root = Path(downloads_root)
        self.downloads_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_valid_course_code(course_code: str) -> bool:
        """
        Check if a course code is valid format (3 letters + 3 digits).

        Examples of valid codes:
        - MIS271, MIS999, CHM101, ENG202, BIO333, PHY101

        Args:
            course_code: Course code to validate

        Returns:
            True if valid format, False otherwise
        """
        return bool(CourseManager.COURSE_CODE_PATTERN.match(course_code))

    def _get_course_info(self, course_code: str) -> dict:
        """
        Get course information, using known metadata or defaults for unknown courses.

        Args:
            course_code: Course code (e.g., "MIS271")

        Returns:
            Dictionary with course info
        """
        # Check if it's a known course with custom metadata
        if course_code in self.KNOWN_COURSES:
            return self.KNOWN_COURSES[course_code]

        # For unknown courses, use defaults
        return {
            "name": f"{course_code} Course",
            "obsidian_folder": self.DEFAULT_OBSIDIAN_FOLDER_TEMPLATE.format(
                course_code=course_code
            ),
            "weeks": self.DEFAULT_WEEKS,
        }

    def get_course_session(
        self, course_code: str, week_number: int, session_type: str = "lecture"
    ) -> CourseSession:
        """
        Get or create a CourseSession object.

        Args:
            course_code: Course code (e.g., "MIS271", "CHM101", etc.)
                        Must be 3 letters followed by 3 digits
            week_number: Week number (1-11 by default, or custom for known courses)
            session_type: "lecture" or "prac"

        Returns:
            CourseSession object

        Raises:
            ValueError: If course code format is invalid or parameters are invalid
        """
        # Validate course code format
        if not self.is_valid_course_code(course_code):
            raise ValueError(
                f"Invalid course code format: {course_code}. "
                f"Expected format: 3 letters + 3 digits (e.g., MIS271, CHM101)"
            )

        course_info = self._get_course_info(course_code)

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
        """Get statistics about available sessions (discovered dynamically)."""
        available = self.list_available_sessions()

        stats = {
            "total_sessions": len(available),
            "by_course": {},
        }

        # Group by unique course codes found (dynamically discovered)
        unique_courses = set(s[0] for s in available)
        for course_code in sorted(unique_courses):
            course_sessions = [s for s in available if s[0] == course_code]
            stats["by_course"][course_code] = {
                "total": len(course_sessions),
                "lectures": len([s for s in course_sessions if s[2] == "lecture"]),
                "pracs": len([s for s in course_sessions if s[2] == "prac"]),
            }

        return stats
