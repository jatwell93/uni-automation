"""Tests for generate_notes helper functions."""

import pytest
from pathlib import Path

from generate_notes import gather_supplementary_context


class TestGatherSupplementaryContext:
    def test_picks_up_md_file(self, tmp_path):
        md_file = tmp_path / "reading_ibm.com_olap-vs-oltp.md"
        md_file.write_text("# OLAP vs OLTP\nSome content.", encoding="utf-8")

        context, found = gather_supplementary_context(tmp_path)

        assert "reading_ibm.com_olap-vs-oltp.md" in found
        assert "READING: reading_ibm.com_olap-vs-oltp.md" in context
        assert "OLAP vs OLTP" in context

    def test_md_file_labelled_as_reading(self, tmp_path):
        (tmp_path / "reading_example.md").write_text("Content", encoding="utf-8")

        context, _ = gather_supplementary_context(tmp_path)

        assert context.startswith("--- READING:")

    def test_empty_folder_returns_empty(self, tmp_path):
        context, found = gather_supplementary_context(tmp_path)
        assert context == ""
        assert found == []

    def test_transcript_txt_skipped(self, tmp_path):
        (tmp_path / "transcript.txt").write_text("raw transcript", encoding="utf-8")

        context, found = gather_supplementary_context(tmp_path)

        assert found == []
        assert context == ""

    def test_md_and_txt_both_included(self, tmp_path):
        (tmp_path / "notes.txt").write_text("Extra notes", encoding="utf-8")
        (tmp_path / "reading_example.md").write_text("Web reading", encoding="utf-8")

        context, found = gather_supplementary_context(tmp_path)

        assert len(found) == 2
        assert "Extra notes" in context
        assert "Web reading" in context


from unittest.mock import patch, Mock


class TestProcessLectureUrlFetching:
    """Verify that --urls causes fetch_url_to_file to be called."""

    def _make_transcript(self, tmp_path):
        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Hello world lecture content here.", encoding="utf-8")
        return transcript

    def test_urls_fetched_before_context_gathering(self, tmp_path):
        transcript = self._make_transcript(tmp_path)

        with patch("generate_notes.CourseManager") as mock_cm, \
             patch("generate_notes.fetch_url_to_file") as mock_fetch, \
             patch("generate_notes.url_to_filename", return_value="reading_example.md"), \
             patch("generate_notes.TranscriptProcessor") as mock_tp, \
             patch("generate_notes.LLMGenerator") as mock_llm, \
             patch("generate_notes.CostTracker") as mock_ct, \
             patch("generate_notes.FrontmatterGenerator") as mock_fm, \
             patch("generate_notes.MarkdownValidator") as mock_mv:

            mock_cm.return_value.find_transcript.return_value = transcript
            mock_tp.return_value.process.return_value = Mock(
                status="success", error_message=None,
                cleaned_text="cleaned", word_count=10, original_word_count=15
            )
            mock_llm.return_value.generate_notes.return_value = Mock(
                status="success", content="# Notes",
                input_tokens=100, output_tokens=50, cost_aud=0.001,
                error_message=None
            )
            mock_fm.return_value.generate_frontmatter.return_value = "---\ntitle: test\n---\n"
            mock_mv.return_value.is_valid_markdown.return_value = (True, [])
            mock_ct.return_value.alert_if_over_budget.return_value = (False, "")

            vault = tmp_path / "vault"
            vault.mkdir()

            from generate_notes import process_lecture
            process_lecture(
                course_code="MIS271", week=1, session="lecture",
                model="deepseek/deepseek-chat", api_key="key",
                vault_path=vault, estimate_only=False,
                urls=["https://example.com/article"],
            )

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][0] == "https://example.com/article"

    def test_no_urls_skips_fetching(self, tmp_path):
        transcript = self._make_transcript(tmp_path)

        with patch("generate_notes.CourseManager") as mock_cm, \
             patch("generate_notes.fetch_url_to_file") as mock_fetch, \
             patch("generate_notes.TranscriptProcessor") as mock_tp, \
             patch("generate_notes.LLMGenerator") as mock_llm, \
             patch("generate_notes.CostTracker") as mock_ct, \
             patch("generate_notes.FrontmatterGenerator") as mock_fm, \
             patch("generate_notes.MarkdownValidator") as mock_mv:

            mock_cm.return_value.find_transcript.return_value = transcript
            mock_tp.return_value.process.return_value = Mock(
                status="success", error_message=None,
                cleaned_text="cleaned", word_count=10, original_word_count=15
            )
            mock_llm.return_value.generate_notes.return_value = Mock(
                status="success", content="# Notes",
                input_tokens=100, output_tokens=50, cost_aud=0.001,
                error_message=None
            )
            mock_fm.return_value.generate_frontmatter.return_value = "---\ntitle: test\n---\n"
            mock_mv.return_value.is_valid_markdown.return_value = (True, [])
            mock_ct.return_value.alert_if_over_budget.return_value = (False, "")

            vault = tmp_path / "vault"
            vault.mkdir()

            from generate_notes import process_lecture
            process_lecture(
                course_code="MIS271", week=1, session="lecture",
                model="deepseek/deepseek-chat", api_key="key",
                vault_path=vault, estimate_only=False,
                urls=[],
            )

        mock_fetch.assert_not_called()
