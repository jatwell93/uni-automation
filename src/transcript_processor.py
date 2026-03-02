"""Transcript processing pipeline for parsing, cleaning, and PII removal from Panopto transcripts."""

import re
import logging
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TranscriptResult:
    """Result of transcript processing operation."""

    status: str  # "success", "missing", "error"
    cleaned_text: Optional[str] = None
    word_count: Optional[int] = None
    original_word_count: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class PIIResult:
    """Result of PII detection operation."""

    total_found: int
    emails_count: int
    names_count: int
    student_ids_count: int
    phone_numbers_count: int
    emails: List[str]
    names: List[str]
    student_ids: List[str]
    phone_numbers: List[str]


class TranscriptError(Exception):
    """Exception raised when transcript processing fails."""

    pass


class PIIDetector:
    """Detect and optionally remove personally identifying information from text."""

    # Common first and last names (conservative list for student names)
    COMMON_STUDENT_NAMES = {
        # Common first names
        "john",
        "jane",
        "james",
        "mary",
        "robert",
        "michael",
        "william",
        "david",
        "richard",
        "joseph",
        "thomas",
        "charles",
        "patricia",
        "jennifer",
        "linda",
        "barbara",
        "elizabeth",
        "susan",
        "jessica",
        "sarah",
        "karen",
        "nancy",
        "betty",
        "margaret",
        "sandra",
        "ashley",
        "kimberly",
        "emily",
        "donna",
        "michelle",
        "dorothy",
        "carol",
        "amanda",
        "melissa",
        "deborah",
        "stephanie",
        "rebecca",
        "sharon",
        "laura",
        "cynthia",
        "katherine",
        "amy",
        "angela",
        "shirley",
        "anna",
        "brenda",
        "pamela",
        "nicole",
        "samantha",
        "katherine",
        "christine",
        "debra",
        "rachel",
        "catherine",
        "carolyn",
        "janet",
        "ruth",
        "marie",
        "kayla",
        "alexis",
        "lori",
        "alice",
        "jean",
        "abigail",
        "sophia",
        "julia",
        "ruby",
        "hannah",
        "olivia",
        "charlotte",
        "mia",
        "amelia",
        # Common last names
        "smith",
        "johnson",
        "williams",
        "brown",
        "jones",
        "garcia",
        "miller",
        "davis",
        "rodriguez",
        "martinez",
        "hernandez",
        "lopez",
        "gonzalez",
        "wilson",
        "anderson",
        "thomas",
        "taylor",
        "moore",
        "jackson",
        "martin",
        "lee",
        "perez",
        "thompson",
        "white",
        "harris",
        "sanchez",
        "clark",
        "ramirez",
        "lewis",
        "robinson",
        "walker",
        "young",
        "allen",
        "king",
        "wright",
        "scott",
        "torres",
        "peterson",
        "phillips",
        "campbell",
        "parker",
        "evans",
        "edwards",
        "collins",
        "reyes",
        "stewart",
        "morris",
        "morales",
        "murphy",
        "cook",
        "rogers",
        "gutierrez",
        "ortiz",
        "morgan",
        "cooper",
        "peterson",
        "rice",
        "howard",
        "ward",
        "cox",
        "richardson",
    }

    # Email regex pattern
    EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    # Student ID patterns: 7-8 digits, optional S prefix
    STUDENT_ID_PATTERN = r"\b[Ss]?\d{7,8}\b"

    # Phone number patterns
    US_PHONE_PATTERN = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
    INTL_PHONE_PATTERN = r"\+\d{1,3}\s?\d{9,}"

    @staticmethod
    def detect_pii(text: str) -> PIIResult:
        """
        Detect PII in text using pattern matching.

        Args:
            text: Text to scan for PII

        Returns:
            PIIResult with detected PII organized by category
        """
        if not text or not isinstance(text, str):
            return PIIResult(
                total_found=0,
                emails_count=0,
                names_count=0,
                student_ids_count=0,
                phone_numbers_count=0,
                emails=[],
                names=[],
                student_ids=[],
                phone_numbers=[],
            )

        try:
            # Detect emails
            emails = list(set(re.findall(PIIDetector.EMAIL_PATTERN, text)))

            # Detect student IDs
            student_ids = list(set(re.findall(PIIDetector.STUDENT_ID_PATTERN, text)))

            # Detect student names (conservative: match common names)
            names = []
            words = re.findall(r"\b[A-Z][a-z]+\b", text)  # Capitalized words
            for word in words:
                if word.lower() in PIIDetector.COMMON_STUDENT_NAMES:
                    if word not in names:
                        names.append(word)

            # Detect phone numbers
            phone_numbers = []
            us_phones = list(set(re.findall(PIIDetector.US_PHONE_PATTERN, text)))
            intl_phones = list(set(re.findall(PIIDetector.INTL_PHONE_PATTERN, text)))
            phone_numbers = us_phones + intl_phones

            total_found = (
                len(emails) + len(names) + len(student_ids) + len(phone_numbers)
            )

            return PIIResult(
                total_found=total_found,
                emails_count=len(emails),
                names_count=len(names),
                student_ids_count=len(student_ids),
                phone_numbers_count=len(phone_numbers),
                emails=emails,
                names=names,
                student_ids=student_ids,
                phone_numbers=phone_numbers,
            )

        except Exception as e:
            logger.warning(f"Error during PII detection: {e}")
            return PIIResult(
                total_found=0,
                emails_count=0,
                names_count=0,
                student_ids_count=0,
                phone_numbers_count=0,
                emails=[],
                names=[],
                student_ids=[],
                phone_numbers=[],
            )

    @staticmethod
    def remove_pii(text: str, categories: Optional[List[str]] = None) -> str:
        """
        Remove PII from text by replacing with [REDACTED].

        Args:
            text: Text to clean
            categories: List of PII categories to remove. Default: ["emails", "student_ids", "names"]

        Returns:
            Text with PII replaced by [REDACTED]
        """
        if categories is None:
            categories = ["emails", "student_ids", "names"]

        if not text or not isinstance(text, str):
            return text

        try:
            result = text

            # Remove emails
            if "emails" in categories:
                result = re.sub(PIIDetector.EMAIL_PATTERN, "[REDACTED]", result)

            # Remove student IDs
            if "student_ids" in categories:
                result = re.sub(PIIDetector.STUDENT_ID_PATTERN, "[REDACTED]", result)

            # Remove student names (conservative: only remove common names)
            if "names" in categories:
                words = re.findall(r"\b[A-Z][a-z]+\b", result)
                for word in words:
                    if word.lower() in PIIDetector.COMMON_STUDENT_NAMES:
                        result = re.sub(
                            r"\b" + re.escape(word) + r"\b", "[REDACTED]", result
                        )

            # Remove phone numbers (optional, too risky for false positives)
            # if "phone_numbers" in categories:
            #     result = re.sub(PIIDetector.US_PHONE_PATTERN, "[REDACTED]", result)
            #     result = re.sub(PIIDetector.INTL_PHONE_PATTERN, "[REDACTED]", result)

            # Normalize whitespace (replace multiple [REDACTED] with single one)
            result = re.sub(r"\[REDACTED\]\s+\[REDACTED\]", "[REDACTED]", result)

            return result

        except Exception as e:
            logger.warning(f"Error during PII removal: {e}")
            return text

    @staticmethod
    def log_pii_findings(pii_result: PIIResult, config=None):
        """
        Log PII detection findings to logger.

        Args:
            pii_result: PIIResult from detect_pii()
            config: ConfigModel with remove_pii_from_transcript flag (optional)
        """
        if pii_result.total_found == 0:
            logger.info("✓ No PII detected in transcript")
            return

        message = (
            f"PII Detection: Found {pii_result.total_found} items "
            f"({pii_result.emails_count} emails, "
            f"{pii_result.student_ids_count} student IDs, "
            f"{pii_result.names_count} names"
        )

        # Check if removal is enabled
        if config and hasattr(config, "remove_pii_from_transcript"):
            if config.remove_pii_from_transcript:
                logger.warning(message)
                logger.info("✓ PII will be removed from transcript before LLM call")
            else:
                logger.warning(message)
                logger.warning(
                    "⚠ PII detected in transcript. "
                    "Set remove_pii_from_transcript=true in config to remove before LLM call"
                )
        else:
            logger.warning(message)


# Module-level helper functions for backward compatibility
def parse_transcript(file_path: Path) -> str:
    """Parse transcript file and extract raw text."""
    processor = TranscriptProcessor()
    return processor.parse_transcript(file_path)


def clean_transcript(raw_text: str) -> str:
    """Clean transcript by removing timestamps, filler words, metadata."""
    processor = TranscriptProcessor()
    return processor.clean_transcript(raw_text)


def strip_pii(text: str) -> str:
    """Remove personally identifying information from text."""
    processor = TranscriptProcessor()
    return processor.strip_pii(text)


class TranscriptProcessor:
    """Parse and clean transcripts from Panopto (VTT, SRT, TXT formats)."""

    def __init__(self):
        """Initialize processor with common filler words."""
        self.filler_words = {
            "um",
            "uh",
            "like",
            "you know",
            "basically",
            "literally",
            "actually",
            "so",
            "just",
            "right",
            "well",
            "anyway",
            "kind of",
            "sort of",
            "i mean",
            "you know what",
        }

    def parse_transcript(self, file_path: Path) -> str:
        """
        Parse transcript file (VTT, SRT, or TXT) and extract raw text.

        Args:
            file_path: Path to transcript file

        Returns:
            Raw transcript text (one string)

        Raises:
            TranscriptError: If file missing, unreadable, or unsupported format
        """
        file_path = Path(file_path)

        # Check if file exists
        if not file_path.exists():
            raise TranscriptError(f"Transcript file not found: {file_path}")

        # Read file with UTF-8 encoding (handle BOM for VTT files)
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except UnicodeDecodeError:
            raise TranscriptError(
                "Cannot read transcript file (encoding error). Ensure UTF-8 format."
            )
        except IOError as e:
            raise TranscriptError(f"Error reading transcript file: {e}")

        # Check if file is empty
        if not content.strip():
            raise TranscriptError("Transcript file is empty. Check Panopto download.")

        # Detect format and parse accordingly
        if "WEBVTT" in content:
            return self._parse_vtt(content)
        elif self._is_srt_format(content):
            return self._parse_srt(content)
        else:
            # Assume plain text
            return content.strip()

    def _parse_vtt(self, content: str) -> str:
        """Parse WebVTT format transcript."""
        lines = content.split("\n")
        text_lines = []

        for i, line in enumerate(lines):
            line = line.strip()
            # Skip header and timestamp lines
            if (
                line.startswith("WEBVTT")
                or "-->" in line
                or line.startswith("NOTE")
                or not line
            ):
                continue
            # Skip metadata in brackets like [Speaker Name]
            if line.startswith("[") and line.endswith("]"):
                continue
            text_lines.append(line)

        return "\n".join(text_lines).strip()

    def _parse_srt(self, content: str) -> str:
        """Parse SRT (SubRip) format transcript."""
        lines = content.split("\n")
        text_lines = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip if this is a sequence number (digits only)
            if line and line.isdigit():
                i += 1
                continue

            # Skip if this is a timestamp line (contains -->)
            if "-->" in line:
                i += 1
                continue

            # Skip empty lines
            if not line:
                i += 1
                continue

            # This is a text line
            text_lines.append(line)
            i += 1

        return "\n".join(text_lines).strip()

    def _is_srt_format(self, content: str) -> bool:
        """Detect if content is in SRT format."""
        lines = content.split("\n")
        timestamp_count = 0
        for line in lines[:20]:  # Check first 20 lines
            if "-->" in line and ":" in line:
                timestamp_count += 1
        return timestamp_count > 0

    def clean_transcript(self, raw_text: str) -> str:
        """
        Clean transcript: remove timestamps, metadata, filler words, URLs.

        Args:
            raw_text: Raw transcript text from parse_transcript()

        Returns:
            Cleaned transcript text
        """
        text = raw_text

        # Remove VTT/SRT timestamps
        # VTT format: 00:00:00.500 --> 00:00:07.000
        text = re.sub(
            r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}", "", text
        )

        # Remove SRT-style timestamps and line numbers
        text = re.sub(r"^\d+\n?", "", text, flags=re.MULTILINE)

        # Remove speaker metadata in brackets [Speaker Name]
        text = re.sub(r"\[\w+\s+\w+\]", "", text)

        # Remove time timestamps in brackets [HH:MM:SS]
        text = re.sub(r"\[\d{2}:\d{2}:\d{2}\]", "", text)

        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)

        # Remove email addresses
        text = re.sub(r"\w+@\w+\.\w+", "", text)

        # Remove filler words (case-insensitive)
        for filler in self.filler_words:
            # Use word boundaries to match whole words only
            pattern = r"\b" + re.escape(filler) + r"\b"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Normalize whitespace: remove multiple spaces
        text = re.sub(r" +", " ", text)

        # Remove multiple newlines (preserve some paragraph breaks)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def strip_pii(self, text: str) -> str:
        """
        Remove personally identifying information from transcript.

        Args:
            text: Cleaned transcript text

        Returns:
            Text with PII stripped (student names, emails, etc.)
        """
        # Email addresses (should already be removed, but double-check)
        text = re.sub(r"\w+@\w+\.\w+", "", text)

        # Student ID patterns like [Student ID: 12345]
        text = re.sub(r"\[Student\s+ID:\s*\d+\]", "", text, flags=re.IGNORECASE)

        # Student name patterns like [Student Name: John Doe]
        text = re.sub(r"\[Student\s+Name:\s*[^\]]+\]", "", text, flags=re.IGNORECASE)

        # Remove isolated numbers that might be student IDs
        # (conservative approach: only remove if clearly marked)

        # Normalize whitespace after PII removal
        text = re.sub(r" +", " ", text)
        text = text.strip()

        return text

    def process(self, file_path: Path) -> TranscriptResult:
        """
        Full pipeline: parse → clean → strip PII.

        Args:
            file_path: Path to transcript file

        Returns:
            TranscriptResult with status, cleaned_text, word_count, error (if any)
        """
        file_path = Path(file_path)

        # Check if file exists
        if not file_path.exists():
            return TranscriptResult(
                status="missing",
                error_message=f"Transcript not found: {file_path}. "
                f"Place transcript file in output folder and re-run.",
            )

        try:
            # Step 1: Parse transcript
            raw_text = self.parse_transcript(file_path)
            original_word_count = len(raw_text.split())

            # Step 2: Clean transcript
            cleaned_text = self.clean_transcript(raw_text)

            # Step 3: Strip PII
            cleaned_text = self.strip_pii(cleaned_text)

            # Calculate final word count
            word_count = len(cleaned_text.split())

            # Validation checks
            if word_count == 0:
                return TranscriptResult(
                    status="error",
                    error_message="Transcript is empty after cleaning. "
                    "Check Panopto download or re-run with fresh transcript.",
                )

            if word_count < 100:
                return TranscriptResult(
                    status="success",
                    cleaned_text=cleaned_text,
                    word_count=word_count,
                    original_word_count=original_word_count,
                    error_message=f"Warning: Transcript very short ({word_count} words). Quality may be poor.",
                )

            # Check if cleaning was too aggressive
            if cleaned_text and original_word_count > 0:
                ratio = word_count / original_word_count
                if ratio < 0.2:
                    return TranscriptResult(
                        status="success",
                        cleaned_text=cleaned_text,
                        word_count=word_count,
                        original_word_count=original_word_count,
                        error_message=f"Warning: Aggressive cleaning removed {100 * (1 - ratio):.0f}% of text. Review for accuracy.",
                    )

            return TranscriptResult(
                status="success",
                cleaned_text=cleaned_text,
                word_count=word_count,
                original_word_count=original_word_count,
            )

        except TranscriptError as e:
            return TranscriptResult(status="error", error_message=str(e))
        except Exception as e:
            return TranscriptResult(
                status="error", error_message=f"Unexpected error: {str(e)}"
            )

    def process_manual_transcript(self, text: str) -> TranscriptResult:
        """
        Process manually-provided transcript text (user pastes content).

        Args:
            text: Manually provided transcript text

        Returns:
            TranscriptResult with cleaned text
        """
        if not text or not text.strip():
            return TranscriptResult(
                status="error", error_message="Manual transcript is empty."
            )

        original_word_count = len(text.split())

        try:
            cleaned_text = self.clean_transcript(text)
            cleaned_text = self.strip_pii(cleaned_text)
            word_count = len(cleaned_text.split())

            return TranscriptResult(
                status="success",
                cleaned_text=cleaned_text,
                word_count=word_count,
                original_word_count=original_word_count,
            )
        except Exception as e:
            return TranscriptResult(
                status="error", error_message=f"Error processing manual transcript: {e}"
            )
