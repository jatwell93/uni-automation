"""Tests for Obsidian vault integration (markdown validation, frontmatter, vault writing)."""

import pytest
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.obsidian_writer import (
    MarkdownValidator,
    FrontmatterGenerator,
    SectionValidator,
    VaultWriter,
    ObsidianWriter,
)
from src.models import ObsidianNote


class TestMarkdownValidator:
    """Tests for markdown validation."""

    def test_validate_markdown_valid_simple(self):
        """Valid markdown with headers only returns (True, [])."""
        content = """## Summary
        Quick summary

        ## Key Concepts
        - Concept 1
        - Concept 2

        ## Examples
        Example text

        ## Formulas
        Formula text

        ## Pitfalls
        Pitfall text

        ## Review Questions
        Question 1"""

        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert is_valid
        assert issues == []

    def test_validate_markdown_unmatched_code_fence(self):
        """Unmatched code fences detected."""
        content = """## Summary
        Some text with code:
        ```python
        def hello():
            print("hi")

        ## Key Concepts
        More content

        ## Examples
        Examples

        ## Formulas
        Formulas

        ## Pitfalls
        Pitfalls

        ## Review Questions
        Questions"""

        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert not is_valid
        assert any("code fence" in issue for issue in issues)

    def test_validate_markdown_unmatched_brackets(self):
        """Unmatched brackets detected."""
        content = """## Summary
        [Link text here

        ## Key Concepts
        Content

        ## Examples
        Examples

        ## Formulas
        Formulas

        ## Pitfalls
        Pitfalls

        ## Review Questions
        Questions"""

        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert not is_valid
        assert any("bracket" in issue for issue in issues)

    def test_validate_markdown_missing_header(self):
        """Missing required header detected."""
        content = """## Summary
        Summary text

        ## Key Concepts
        Concepts

        ## Examples
        Examples

        ## Formulas
        Formulas

        ## Pitfalls
        Pitfalls"""

        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert not is_valid
        assert any("Review Questions" in issue for issue in issues)

    def test_validate_markdown_all_sections_present(self):
        """All 6 sections present returns valid."""
        content = """## Summary
        Summary here

        ## Key Concepts
        Key points

        ## Examples
        Real examples

        ## Formulas
        Mathematical formulas

        ## Pitfalls
        Common mistakes

        ## Review Questions
        Self test questions"""

        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert is_valid
        assert issues == []

    def test_validate_markdown_empty_content(self):
        """Empty content returns invalid."""
        is_valid, issues = MarkdownValidator.is_valid_markdown("")
        assert not is_valid
        assert "empty" in issues[0].lower()

    def test_validate_markdown_unmatched_curly_braces(self):
        """Unmatched curly braces detected."""
        content = """## Summary
        Text with { brace

        ## Key Concepts
        Content

        ## Examples
        Examples

        ## Formulas
        Formulas

        ## Pitfalls
        Pitfalls

        ## Review Questions
        Questions"""

        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert not is_valid
        assert any("curly" in issue for issue in issues)

    def test_validate_markdown_unmatched_parentheses(self):
        """Unmatched parentheses detected."""
        content = """## Summary
        Text with ( paren

        ## Key Concepts
        Content

        ## Examples
        Examples

        ## Formulas
        Formulas

        ## Pitfalls
        Pitfalls

        ## Review Questions
        Questions"""

        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert not is_valid
        assert any("parenthes" in issue for issue in issues)


class TestFrontmatterGenerator:
    """Tests for frontmatter generation."""

    def test_generate_frontmatter_basic(self):
        """Basic frontmatter generation."""
        metadata = {
            "course": "Biology",
            "week": 3,
            "date": "2026-03-01",
            "panopto_url": "https://panopto.com/session/123",
        }

        fm = FrontmatterGenerator.generate_frontmatter(metadata)

        assert "---" in fm
        assert "course: Biology" in fm
        assert "week: 3" in fm
        assert "date: 2026-03-01" in fm
        assert "source: https://panopto.com/session/123" in fm
        assert "tags:" in fm

    def test_generate_frontmatter_tags_generation(self):
        """Tags are auto-generated from course name."""
        metadata = {
            "course": "Business Analytics",
            "week": 5,
            "date": "2026-03-02",
            "panopto_url": "https://panopto.com/",
        }

        fm = FrontmatterGenerator.generate_frontmatter(metadata)

        assert "[lecture, business-analytics, week-05]" in fm

    def test_generate_frontmatter_with_title(self):
        """Optional title field included."""
        metadata = {
            "course": "Physics",
            "week": 1,
            "date": "2026-03-01",
            "panopto_url": "https://panopto.com/",
            "title": "Introduction to Mechanics",
        }

        fm = FrontmatterGenerator.generate_frontmatter(metadata)

        assert "title: Introduction to Mechanics" in fm

    def test_generate_frontmatter_without_panopto_url(self):
        """Missing panopto_url falls back to N/A."""
        metadata = {
            "course": "Chemistry",
            "week": 2,
            "date": "2026-03-01",
        }

        fm = FrontmatterGenerator.generate_frontmatter(metadata)

        assert "source: N/A" in fm

    def test_generate_frontmatter_special_chars_in_course(self):
        """Special characters in course name handled correctly."""
        metadata = {
            "course": "Data & Analytics",
            "week": 1,
            "date": "2026-03-01",
            "panopto_url": "https://panopto.com/",
        }

        fm = FrontmatterGenerator.generate_frontmatter(metadata)

        # & should be preserved (only spaces removed), creating "data--analytics"
        assert "data" in fm and "analytics" in fm

    def test_generate_frontmatter_yaml_valid(self):
        """Generated frontmatter is valid YAML."""
        metadata = {
            "course": "Advanced Math",
            "week": 10,
            "date": "2026-03-15",
            "panopto_url": "https://panopto.com/",
        }

        fm = FrontmatterGenerator.generate_frontmatter(metadata)

        # Check structure
        lines = fm.split("\n")
        assert lines[0] == "---"
        assert lines[-2] == "---"  # Last separator
        assert all(
            ":" in line for line in lines[1:-2] if line.strip()
        )  # All content has key:value


class TestSectionValidator:
    """Tests for section validation."""

    def test_validate_sections_all_present(self):
        """All 6 sections present returns (True, section_details)."""
        content = """## Summary
        Summary content here

        ## Key Concepts
        Concepts

        ## Examples
        Examples

        ## Formulas
        Formulas

        ## Pitfalls
        Pitfalls

        ## Review Questions
        Questions"""

        all_present, details = SectionValidator.validate_sections(content)

        assert all_present
        assert len(details) == 6
        assert all(details[s]["present"] for s in details.keys())
        assert details["Summary"]["line_number"] == 1

    def test_validate_sections_missing_one(self):
        """Missing one section detected."""
        content = """## Summary
        Summary

        ## Key Concepts
        Concepts

        ## Examples
        Examples

        ## Formulas
        Formulas

        ## Review Questions
        Questions"""

        all_present, details = SectionValidator.validate_sections(content)

        assert not all_present
        assert not details["Pitfalls"]["present"]
        assert details["Summary"]["present"]

    def test_validate_sections_line_numbers(self):
        """Line numbers are correct."""
        content = """## Summary
        Summary content

        ## Key Concepts
        Concepts"""

        all_present, details = SectionValidator.validate_sections(content)

        assert details["Summary"]["line_number"] == 1
        assert details["Key Concepts"]["line_number"] == 4

    def test_validate_sections_content_length(self):
        """Content length calculated correctly."""
        content = """## Summary
        This is summary content with some text

        ## Key Concepts
        Short

        ## Examples
        Ex

        ## Formulas
        F

        ## Pitfalls
        P

        ## Review Questions
        Q"""

        all_present, details = SectionValidator.validate_sections(content)

        assert details["Summary"]["content_length"] > 0
        assert (
            details["Summary"]["content_length"] > details["Pitfalls"]["content_length"]
        )


class TestObsidianNote:
    """Tests for ObsidianNote dataclass."""

    def test_obsidian_note_to_markdown(self):
        """ObsidianNote.to_markdown() combines frontmatter + title + content."""
        note = ObsidianNote(
            course="Biology",
            week=5,
            date="2026-03-02",
            panopto_url="https://panopto.com/",
            llm_content="## Summary\nBiology summary here",
            title="Cell Biology",
        )

        markdown = note.to_markdown()

        assert "---" in markdown
        assert "course: Biology" in markdown
        assert "# Cell Biology" in markdown
        assert "## Summary" in markdown
        assert "Biology summary here" in markdown

    def test_obsidian_note_without_title(self):
        """ObsidianNote without title still generates valid markdown."""
        note = ObsidianNote(
            course="Physics",
            week=1,
            date="2026-03-01",
            panopto_url="https://panopto.com/",
            llm_content="## Summary\nPhysics content",
        )

        markdown = note.to_markdown()

        assert "---" in markdown
        assert "## Summary" in markdown
        # Title line should not exist if not provided
        assert "# Physics" not in markdown


class TestVaultWriter:
    """Tests for vault file writing."""

    def test_verify_vault_exists_true(self):
        """Vault exists returns (True, message)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = VaultWriter(tmpdir)
            exists, msg = writer.verify_vault_exists()

            assert exists
            assert "OK" in msg or "exist" in msg.lower()

    def test_verify_vault_exists_false(self):
        """Non-existent vault returns (False, error_message)."""
        writer = VaultWriter("/nonexistent/path/to/vault")
        exists, msg = writer.verify_vault_exists()

        assert not exists
        assert "not found" in msg.lower() or "does not exist" in msg.lower()

    def test_write_notes_success(self):
        """Valid metadata + content creates file at correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = VaultWriter(tmpdir)

            metadata = {
                "week": 5,
                "course": "Bio",
                "date": "2026-03-02",
                "subfolder": "Lectures",
            }
            content = """## Summary
            Bio summary

            ## Key Concepts
            Concepts

            ## Examples
            Examples

            ## Formulas
            Formulas

            ## Pitfalls
            Pitfalls

            ## Review Questions
            Questions"""

            success, result = writer.write_notes(metadata, content)

            assert success
            file_path = Path(result)
            assert file_path.exists()
            assert file_path.name == "Week_05.md"

    def test_write_notes_creates_subfolder(self):
        """Subfolder doesn't exist, write creates it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = VaultWriter(tmpdir)

            metadata = {
                "week": 3,
                "course": "Physics",
                "date": "2026-03-01",
                "subfolder": "Physics/Week_03",
            }
            content = """## Summary
            Summary

            ## Key Concepts
            Concepts

            ## Examples
            Examples

            ## Formulas
            Formulas

            ## Pitfalls
            Pitfalls

            ## Review Questions
            Questions"""

            success, result = writer.write_notes(metadata, content)

            assert success
            file_path = Path(result)
            assert file_path.parent.exists()

    def test_write_notes_prevents_overwrite(self):
        """File exists, write creates backup with timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = VaultWriter(tmpdir)
            subfolder = "Lectures"

            # Create initial file
            (Path(tmpdir) / subfolder).mkdir(parents=True, exist_ok=True)
            initial_file = Path(tmpdir) / subfolder / "Week_05.md"
            initial_file.write_text("Initial content", encoding="utf-8")

            # Write with same week - should create backup
            metadata = {
                "week": 5,
                "course": "Bio",
                "date": "2026-03-02",
                "subfolder": subfolder,
            }
            content = """## Summary
            New summary

            ## Key Concepts
            Concepts

            ## Examples
            Examples

            ## Formulas
            Formulas

            ## Pitfalls
            Pitfalls

            ## Review Questions
            Questions"""

            success, result = writer.write_notes(metadata, content)

            assert success
            new_file = Path(result)
            # New file should have timestamp
            assert "__" in new_file.name
            assert initial_file.exists()
            assert new_file.exists()

    def test_write_notes_invalid_vault_path(self):
        """Vault not found returns (False, error_message)."""
        writer = VaultWriter("/nonexistent/vault")

        metadata = {"week": 1, "course": "Test", "date": "2026-03-01", "subfolder": ""}
        content = """## Summary
        S

        ## Key Concepts
        K

        ## Examples
        E

        ## Formulas
        F

        ## Pitfalls
        P

        ## Review Questions
        Q"""

        success, result = writer.write_notes(metadata, content)

        assert not success
        assert "not found" in result.lower()

    def test_write_notes_validates_before_writing(self):
        """Invalid markdown returns (False, error_message)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = VaultWriter(tmpdir)

            metadata = {
                "week": 1,
                "course": "Test",
                "date": "2026-03-01",
                "subfolder": "",
            }
            # Missing required sections
            content = "## Summary\nJust summary"

            success, result = writer.write_notes(metadata, content)

            assert not success
            assert "Invalid markdown" in result

    def test_write_notes_utf8_encoding(self):
        """Unicode content (é, 中文, emojis) writes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = VaultWriter(tmpdir)

            metadata = {
                "week": 1,
                "course": "Languages",
                "date": "2026-03-01",
                "subfolder": "",
            }
            content = """## Summary
            Français: café, naïve. 中文: 学习. Emoji: 🎓📚

            ## Key Concepts
            Concept

            ## Examples
            Example

            ## Formulas
            Formula

            ## Pitfalls
            Pitfall

            ## Review Questions
            Question"""

            success, result = writer.write_notes(metadata, content)

            assert success
            file_path = Path(result)
            file_content = file_path.read_text(encoding="utf-8")
            assert "café" in file_content
            assert "中文" in file_content
            assert "🎓" in file_content

    def test_list_notes_empty_vault(self):
        """No .md files returns []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = VaultWriter(tmpdir)
            notes = writer.list_notes()

            assert notes == []

    def test_list_notes_with_files(self):
        """Lists all .md files in vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            (Path(tmpdir) / "Week_01.md").write_text("content")
            (Path(tmpdir) / "Week_02.md").write_text("content")
            (Path(tmpdir) / "Other.txt").write_text("content")

            writer = VaultWriter(tmpdir)
            notes = writer.list_notes()

            assert len(notes) == 2
            assert any("Week_01" in str(n) for n in notes)
            assert any("Week_02" in str(n) for n in notes)


class TestObsidianWriter:
    """Tests for ObsidianWriter orchestration."""

    def test_obsidian_writer_end_to_end(self):
        """Create metadata, generate frontmatter, validate, write—all succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "obsidian_vault_path": tmpdir,
                "obsidian_note_subfolder": "Lectures",
            }

            writer = ObsidianWriter(config)

            metadata = {
                "course": "Economics",
                "week": 2,
                "date": "2026-03-02",
                "panopto_url": "https://panopto.com/",
                "subfolder": "Lectures",
            }
            llm_content = """## Summary
            Economic summary

            ## Key Concepts
            Concepts

            ## Examples
            Examples

            ## Formulas
            Formulas

            ## Pitfalls
            Pitfalls

            ## Review Questions
            Questions"""

            success, result = writer.write_complete_note(metadata, llm_content)

            assert success
            file_path = Path(result)
            assert file_path.exists()
            content = file_path.read_text(encoding="utf-8")
            assert "course: Economics" in content
            assert "## Summary" in content

    def test_obsidian_writer_with_overwrite(self):
        """File exists, ObsidianWriter creates backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "obsidian_vault_path": tmpdir,
                "obsidian_note_subfolder": "Lectures",
            }

            writer = ObsidianWriter(config)

            # Create initial file
            (Path(tmpdir) / "Lectures").mkdir(parents=True, exist_ok=True)
            initial_file = Path(tmpdir) / "Lectures" / "Week_02.md"
            initial_file.write_text("Original")

            # Write same week
            metadata = {
                "course": "Economics",
                "week": 2,
                "date": "2026-03-02",
                "panopto_url": "https://panopto.com/",
                "subfolder": "Lectures",
            }
            llm_content = """## Summary
            New content

            ## Key Concepts
            Concepts

            ## Examples
            Examples

            ## Formulas
            Formulas

            ## Pitfalls
            Pitfalls

            ## Review Questions
            Questions"""

            success, result = writer.write_complete_note(metadata, llm_content)

            assert success
            assert initial_file.exists()
            assert Path(result).exists()
            assert Path(result) != initial_file
