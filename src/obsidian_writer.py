"""
Obsidian vault integration for formatted note output.

Includes markdown validation, frontmatter generation, and vault file writing.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class MarkdownValidator:
    """Validate markdown content for formatting issues."""

    @staticmethod
    def is_valid_markdown(content: str) -> Tuple[bool, List[str]]:
        """
        Check markdown validity.

        Args:
            content: Markdown content to validate

        Returns:
            Tuple of (is_valid, list_of_issues). Returns (True, []) if valid.
        """
        issues = []

        if not content:
            issues.append("Content is empty")
            return (False, issues)

        # Check 1: Unmatched code fences
        code_fence_count = content.count("```")
        if code_fence_count % 2 != 0:
            issues.append("Unmatched code fence (``` count must be even)")

        # Check 2: Unmatched square brackets
        if content.count("[") != content.count("]"):
            issues.append("Unmatched square brackets ([ vs ])")

        # Check 3: Unmatched curly braces
        if content.count("{") != content.count("}"):
            issues.append("Unmatched curly braces ({ vs })")

        # Check 4: Unmatched parentheses
        if content.count("(") != content.count(")"):
            issues.append("Unmatched parentheses (( vs ))")

        # Check 5: Required headers
        required_headers = [
            "## Summary",
            "## Key Concepts",
            "## Examples",
            "## Formulas",
            "## Pitfalls",
            "## Review Questions",
        ]

        for header in required_headers:
            if header not in content:
                issues.append(f"Missing {header} section")

        return (len(issues) == 0, issues)


class FrontmatterGenerator:
    """Generate YAML frontmatter for Obsidian notes."""

    @staticmethod
    def generate_frontmatter(lecture_metadata: dict) -> str:
        """
        Create YAML frontmatter block.

        Args:
            lecture_metadata: Dictionary containing:
                - course: str (e.g., "Business Analytics")
                - week: int (e.g., 5)
                - date: str (ISO format, e.g., "2026-03-02")
                - panopto_url: str (e.g., "https://panopto.com/...")
                - title (optional): str for lecture title

        Returns:
            YAML frontmatter block as string
        """
        course = lecture_metadata.get("course", "Unknown Course")
        week = lecture_metadata.get("week", 0)
        date = lecture_metadata.get("date", "")
        panopto_url = lecture_metadata.get("panopto_url", "N/A")
        title = lecture_metadata.get("title", "")

        # Generate tags
        course_slug = course.lower().replace(" ", "-").replace("&", "")
        tags = ["lecture", course_slug, f"week-{week:02d}"]
        tags_str = "[" + ", ".join(tags) + "]"

        # Build frontmatter
        fm = "---\n"
        fm += f"course: {course}\n"
        fm += f"week: {week}\n"
        fm += f"date: {date}\n"
        fm += f"tags: {tags_str}\n"
        fm += f"source: {panopto_url}\n"
        if title:
            fm += f"title: {title}\n"
        fm += "---\n"

        return fm


class SectionValidator:
    """Parse and validate markdown sections."""

    REQUIRED_SECTIONS = [
        "Summary",
        "Key Concepts",
        "Examples",
        "Formulas",
        "Pitfalls",
        "Review Questions",
    ]

    @staticmethod
    def validate_sections(content: str) -> Tuple[bool, Dict]:
        """
        Parse generated markdown and verify 6 sections exist.

        Args:
            content: Markdown content to validate

        Returns:
            Tuple of (all_present, section_details)
            section_details: {section_name: {present: bool, line_number: int, content_length: int}}
        """
        section_details = {}
        lines = content.split("\n")

        all_present = True

        for section_name in SectionValidator.REQUIRED_SECTIONS:
            section_header = f"## {section_name}"
            present = False
            line_number = -1
            content_length = 0

            for i, line in enumerate(lines):
                if section_header in line:
                    present = True
                    line_number = i + 1  # 1-indexed

                    # Find content until next section or end
                    content_start = i + 1
                    content_end = len(lines)

                    for j in range(content_start, len(lines)):
                        if lines[j].startswith("## "):
                            content_end = j
                            break

                    section_content = "\n".join(lines[content_start:content_end])
                    content_length = len(section_content.strip())
                    break

            if not present:
                all_present = False

            section_details[section_name] = {
                "present": present,
                "line_number": line_number,
                "content_length": content_length,
            }

        return (all_present, section_details)


@dataclass
class ObsidianNote:
    """Structured note metadata for Obsidian."""

    course: str
    week: int
    date: str
    panopto_url: str
    llm_content: str
    title: str = ""
    frontmatter: str = ""

    def to_markdown(self) -> str:
        """
        Combine frontmatter + title header + content.

        Returns:
            Complete markdown note as string
        """
        # Generate frontmatter if not provided
        if not self.frontmatter:
            fm_generator = FrontmatterGenerator()
            self.frontmatter = fm_generator.generate_frontmatter(
                {
                    "course": self.course,
                    "week": self.week,
                    "date": self.date,
                    "panopto_url": self.panopto_url,
                    "title": self.title,
                }
            )

        # Build complete markdown
        markdown = self.frontmatter

        if self.title:
            markdown += f"\n# {self.title}\n\n"

        markdown += self.llm_content

        return markdown


class VaultWriter:
    """Write formatted notes to Obsidian vault."""

    def __init__(
        self, vault_path: str, logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize VaultWriter.

        Args:
            vault_path: Path to Obsidian vault root
            logger_instance: Optional logger instance
        """
        self.vault_path = Path(vault_path)
        self.logger = logger_instance or logger

    def verify_vault_exists(self) -> Tuple[bool, str]:
        """
        Check if vault_path exists as directory.

        Returns:
            Tuple of (exists, message)
        """
        if self.vault_path.exists() and self.vault_path.is_dir():
            return (True, "Vault OK")
        else:
            return (
                False,
                f"Vault not found at {self.vault_path}. Create folder or update obsidian_vault_path in config.",
            )

    def write_notes(self, metadata: dict, content: str) -> Tuple[bool, str]:
        """
        Full write pipeline.

        Args:
            metadata: Dictionary with week, course, date, subfolder
            content: Markdown content to write

        Returns:
            Tuple of (success, file_path_or_error)
        """
        # Validate vault exists
        exists, msg = self.verify_vault_exists()
        if not exists:
            return (False, msg)

        try:
            # Ensure subfolder exists
            subfolder = metadata.get("subfolder", "")
            if subfolder:
                vault_subfolder = self.vault_path / subfolder
            else:
                vault_subfolder = self.vault_path

            vault_subfolder.mkdir(parents=True, exist_ok=True)

            # Generate filename
            week = metadata.get("week")
            if isinstance(week, int):
                filename = f"Week_{week:02d}.md"
            else:
                date_str = metadata.get("date", "")
                course = metadata.get("course", "Note").replace(" ", "_")
                filename = f"{date_str}_{course}.md"

            file_path = vault_subfolder / filename

            # Check for conflicts
            if file_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{filename.replace('.md', '')}__{timestamp}.md"
                backup_path = vault_subfolder / backup_filename
                self.logger.warning(
                    f"File exists at {file_path}. Saving as {backup_path}"
                )
                file_path = backup_path

            # Validate markdown before writing
            validator = MarkdownValidator()
            is_valid, issues = validator.is_valid_markdown(content)
            if not is_valid:
                error_msg = f"Invalid markdown generated: {', '.join(issues)}. This is a bug—please report with transcript."
                self.logger.error(error_msg)
                return (False, error_msg)

            # Write file with UTF-8 encoding
            file_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Wrote notes to {file_path}")

            return (True, str(file_path))

        except PermissionError as e:
            error_msg = f"Cannot create subfolder {subfolder}: {str(e)}. Check folder permissions."
            self.logger.error(error_msg)
            return (False, error_msg)

        except Exception as e:
            error_msg = f"Error writing notes: {str(e)}"
            self.logger.error(error_msg)
            return (False, error_msg)

    def list_notes(self) -> List[str]:
        """
        Return list of .md files in vault.

        Returns:
            List of .md file paths as strings
        """
        if not self.vault_path.exists():
            return []

        md_files = list(self.vault_path.rglob("*.md"))
        return [str(f) for f in sorted(md_files)]


class ObsidianWriter:
    """Orchestrates markdown validation and vault writing."""

    def __init__(self, config: dict, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize ObsidianWriter.

        Args:
            config: Configuration dict with obsidian_vault_path
            logger_instance: Optional logger instance
        """
        self.vault_path = config.get("obsidian_vault_path", "")
        self.note_subfolder = config.get("obsidian_note_subfolder", "Lectures")
        self.logger = logger_instance or logger
        self.vault_writer = VaultWriter(self.vault_path, self.logger)

    def write_complete_note(self, metadata: dict, llm_content: str) -> Tuple[bool, str]:
        """
        One-shot method: generate frontmatter, validate, write.

        Args:
            metadata: Dictionary with course, week, date, panopto_url, subfolder
            llm_content: LLM-generated markdown content

        Returns:
            Tuple of (success, file_path_or_error_message)
        """
        try:
            # Add default subfolder if not provided
            if "subfolder" not in metadata:
                metadata["subfolder"] = self.note_subfolder

            # Generate frontmatter
            fm_generator = FrontmatterGenerator()
            frontmatter = fm_generator.generate_frontmatter(metadata)

            # Combine frontmatter + content
            complete_markdown = frontmatter + "\n" + llm_content

            # Validate combined markdown
            validator = MarkdownValidator()
            is_valid, issues = validator.is_valid_markdown(complete_markdown)
            if not is_valid:
                error_msg = f"Invalid markdown: {', '.join(issues)}"
                self.logger.error(error_msg)
                return (False, error_msg)

            # Write to vault
            return self.vault_writer.write_notes(metadata, complete_markdown)

        except Exception as e:
            error_msg = f"Error in write_complete_note: {str(e)}"
            self.logger.error(error_msg)
            return (False, error_msg)
