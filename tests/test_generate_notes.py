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
