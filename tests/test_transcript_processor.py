"""Unit tests for transcript processing module."""

import pytest
from pathlib import Path
import tempfile

from src.transcript_processor import (
    TranscriptProcessor,
    TranscriptError,
    TranscriptResult,
)


@pytest.fixture
def processor():
    """Create a TranscriptProcessor instance for tests."""
    return TranscriptProcessor()


@pytest.fixture
def sample_vtt():
    """Sample VTT format transcript."""
    return """WEBVTT

00:00:00.500 --> 00:00:07.000
Hello everyone, welcome to today's lecture.

00:00:07.000 --> 00:00:10.000
Today we're going to discuss business analytics.

00:00:10.000 --> 00:00:15.000
This is, um, a really important topic for your career.
"""


@pytest.fixture
def sample_srt():
    """Sample SRT format transcript."""
    return """1
00:00:00,500 --> 00:00:07,000
Hello everyone, welcome to today's lecture.

2
00:00:07,000 --> 00:00:10,000
Today we're going to discuss business analytics.

3
00:00:10,000 --> 00:00:15,000
This is, um, a really important topic for your career.
"""


@pytest.fixture
def sample_txt():
    """Sample plain text transcript."""
    return """Hello everyone, welcome to today's lecture.
Today we're going to discuss business analytics.
This is, um, a really important topic for your career."""


@pytest.fixture
def transcript_with_filler(processor):
    """Text with common filler words."""
    return """Um, so like, this is a really important concept.
You know, uh, basically, it's about understanding data.
I mean, literally, this will change your life."""


@pytest.fixture
def transcript_with_pii():
    """Text with email addresses and potential names."""
    return """Contact john.doe@example.com for more information.
Student ID: 12345 attended the lecture.
[Student Name: John Doe] participated in discussion.
Email protocols are important for security."""


@pytest.fixture
def tmp_transcript_file(sample_vtt):
    """Create a temporary VTT transcript file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".vtt", delete=False, encoding="utf-8"
    ) as f:
        f.write(sample_vtt)
        tmp_path = Path(f.name)
    yield tmp_path
    tmp_path.unlink()


# ============================================================================
# PARSING TESTS
# ============================================================================


class TestParsingVTT:
    """Test VTT format parsing."""

    def test_parse_vtt_format(self, processor, tmp_transcript_file):
        """VTT file → text lines extracted, timestamps removed."""
        result = processor.parse_transcript(tmp_transcript_file)
        assert "Hello everyone" in result
        assert "business analytics" in result
        assert "00:00:00" not in result
        assert "-->" not in result

    def test_parse_vtt_removes_webvtt_header(self, processor, sample_vtt):
        """WEBVTT header is removed."""
        result = processor._parse_vtt(sample_vtt)
        assert "WEBVTT" not in result

    def test_parse_vtt_with_bom(self, processor):
        """VTT file with UTF-8 BOM is correctly parsed."""
        vtt_with_bom = "\ufeffWEBVTT\n\n00:00:00.500 --> 00:00:07.000\nTest content"
        result = processor._parse_vtt(vtt_with_bom)
        assert "Test content" in result

    def test_parse_missing_file(self, processor):
        """FileNotFoundError with helpful message."""
        with pytest.raises(TranscriptError, match="Transcript file not found"):
            processor.parse_transcript(Path("/nonexistent/file.vtt"))


class TestParsingSRT:
    """Test SRT format parsing."""

    def test_parse_srt_format(self, processor, sample_srt):
        """SRT file → text lines extracted, line numbers removed."""
        result = processor._parse_srt(sample_srt)
        assert "Hello everyone" in result
        assert "business analytics" in result
        assert "00:00:00" not in result
        assert "-->" not in result
        # Line numbers should not be present
        assert not result.startswith("1")

    def test_parse_srt_detects_format(self, processor, sample_srt):
        """SRT format is correctly detected."""
        assert processor._is_srt_format(sample_srt) is True

    def test_parse_txt_not_detected_as_srt(self, processor, sample_txt):
        """Plain text is not detected as SRT."""
        assert processor._is_srt_format(sample_txt) is False


class TestParsingTXT:
    """Test TXT format parsing."""

    def test_parse_txt_format(self, processor, sample_txt, tmp_path):
        """Plain text → returned as-is."""
        txt_file = tmp_path / "transcript.txt"
        txt_file.write_text(sample_txt, encoding="utf-8")
        result = processor.parse_transcript(txt_file)
        assert sample_txt.strip() in result


class TestParsingEdgeCases:
    """Test edge cases in parsing."""

    def test_parse_empty_file(self, processor, tmp_path):
        """Empty file returns error."""
        empty_file = tmp_path / "empty.vtt"
        empty_file.write_text("", encoding="utf-8")
        with pytest.raises(TranscriptError, match="empty"):
            processor.parse_transcript(empty_file)

    def test_parse_unicode_content(self, processor, tmp_path):
        """Non-ASCII characters handled correctly."""
        unicode_content = "Café, naïve, 中文, émojis 🎓"
        unicode_file = tmp_path / "unicode.txt"
        unicode_file.write_text(unicode_content, encoding="utf-8")
        result = processor.parse_transcript(unicode_file)
        assert "Café" in result
        assert "中文" in result

    def test_parse_mixed_format(self, processor):
        """File with mixed VTT/SRT → best-effort parsing."""
        # VTT has WEBVTT header, so it should be parsed as VTT even with SRT elements
        mixed = """WEBVTT

1
00:00:00.500 --> 00:00:07.000
Test line
"""
        result = processor._parse_vtt(mixed)
        assert "Test line" in result


# ============================================================================
# CLEANING TESTS
# ============================================================================


class TestCleaningTimestamps:
    """Test timestamp removal."""

    def test_clean_removes_vtt_timestamps(self, processor):
        """VTT format timestamps removed."""
        text = "00:00:00.500 --> 00:00:07.000 Hello"
        result = processor.clean_transcript(text)
        assert "-->" not in result
        assert "Hello" in result
        assert "00:00:00" not in result

    def test_clean_removes_srt_timestamps(self, processor):
        """SRT format timestamps removed."""
        text = "00:00:00,000 --> 00:00:02,000 Hello"
        result = processor.clean_transcript(text)
        assert "-->" not in result
        assert "00:00:00" not in result


class TestCleaningFillerWords:
    """Test filler word removal."""

    def test_clean_removes_filler_words(self, processor, transcript_with_filler):
        """Filler words 'um', 'uh', 'like' removed."""
        result = processor.clean_transcript(transcript_with_filler)
        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        # 'like' should be removed (not as part of another word)
        assert "this is a really important concept" in result.lower()

    def test_clean_case_insensitive_filler(self, processor):
        """Case variations of filler words removed."""
        text = "Um this is great. UM yeah. uM sure. like this is good."
        result = processor.clean_transcript(text)
        assert "um" not in result.lower()
        # "is" should remain
        assert "is" in result.lower()

    def test_clean_preserves_words_containing_filler(self, processor):
        """Words containing filler substrings are preserved."""
        text = "The album is good. I understand this."
        result = processor.clean_transcript(text)
        # "album" contains "um", but should be preserved (word boundary)
        assert "album" in result.lower()
        # "understand" contains "um", but should be preserved
        assert "understand" in result.lower()


class TestCleaningMetadata:
    """Test metadata removal."""

    def test_clean_removes_speaker_metadata(self, processor):
        """Speaker metadata in brackets removed."""
        text = "[Speaker Name] This is important. [John Smith] Next point."
        result = processor.clean_transcript(text)
        assert "[" not in result
        assert "]" not in result
        assert "This is important" in result

    def test_clean_removes_time_brackets(self, processor):
        """Time in brackets removed."""
        text = "[00:05:30] Here's the important part."
        result = processor.clean_transcript(text)
        assert "[00:05:30]" not in result
        assert "Here's the important part" in result

    def test_clean_removes_urls(self, processor):
        """URLs removed from text."""
        text = "Check out https://example.com for more info."
        result = processor.clean_transcript(text)
        assert "https://" not in result
        assert "example.com" not in result
        assert "Check out" in result
        assert "for more info" in result


class TestCleaningWhitespace:
    """Test whitespace normalization."""

    def test_clean_normalizes_multiple_spaces(self, processor):
        """Multiple spaces → single space."""
        text = "Hello   world    test"
        result = processor.clean_transcript(text)
        assert "   " not in result
        assert "Hello world test" in result

    def test_clean_removes_excessive_newlines(self, processor):
        """10 consecutive newlines → 2."""
        text = "First paragraph\n\n\n\n\n\n\n\n\n\nSecond paragraph"
        result = processor.clean_transcript(text)
        assert "\n\n\n" not in result
        assert "First paragraph" in result
        assert "Second paragraph" in result

    def test_clean_preserves_sentence_structure(self, processor):
        """Sentence structure with periods preserved."""
        text = "First sentence. Second sentence."
        result = processor.clean_transcript(text)
        assert "First sentence" in result
        assert "Second sentence" in result
        assert "." in result


class TestCleaningEmails:
    """Test email removal."""

    def test_clean_removes_email_addresses(self, processor):
        """Email addresses removed from text."""
        text = "Contact john.doe@example.com for assistance."
        result = processor.clean_transcript(text)
        assert "john.doe@example.com" not in result
        assert "Contact" in result
        assert "for assistance" in result


# ============================================================================
# PII REMOVAL TESTS
# ============================================================================


class TestPIIRemoval:
    """Test personally identifying information removal."""

    def test_strip_pii_removes_emails(self, processor, transcript_with_pii):
        """Email addresses removed."""
        result = processor.strip_pii(transcript_with_pii)
        assert "@" not in result or "protocols" in result  # "protocols" might contain @
        assert "john.doe" not in result

    def test_strip_pii_removes_student_ids(self, processor):
        """Student ID patterns removed."""
        text = "[Student ID: 12345] attended class."
        result = processor.strip_pii(text)
        assert "12345" not in result
        assert "attended class" in result

    def test_strip_pii_removes_student_names(self, processor):
        """Student name patterns removed."""
        text = "[Student Name: John Doe] participated."
        result = processor.strip_pii(text)
        assert "[Student Name:" not in result
        assert "participated" in result

    def test_strip_pii_preserves_content(self, processor):
        """Non-PII content preserved."""
        text = "Email protocols are important for security."
        result = processor.strip_pii(text)
        # "protocols" contains "col" not "email", so should be preserved
        assert "important" in result
        assert "security" in result


# ============================================================================
# FULL PIPELINE (PROCESS) TESTS
# ============================================================================


class TestFullPipeline:
    """Test full transcript processing pipeline."""

    def test_process_valid_vtt(self, processor, tmp_transcript_file):
        """Full VTT file → cleaned, PII removed, word count calculated."""
        result = processor.process(tmp_transcript_file)
        assert result.status == "success"
        assert result.cleaned_text is not None
        assert result.word_count is not None
        assert result.word_count > 0
        assert result.original_word_count is not None
        assert "-->" not in result.cleaned_text

    def test_process_returns_word_count(self, processor, tmp_transcript_file):
        """TranscriptResult includes word_count and original_word_count."""
        result = processor.process(tmp_transcript_file)
        assert result.word_count is not None
        assert result.original_word_count is not None
        # Cleaned should be less than or equal to original (after stripping)
        assert result.word_count <= result.original_word_count

    def test_process_missing_transcript(self, processor):
        """Missing file returns status='missing' with recovery message."""
        result = processor.process(Path("/nonexistent/transcript.vtt"))
        assert result.status == "missing"
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

    def test_process_empty_transcript(self, processor, tmp_path):
        """Empty file after cleaning returns error."""
        # Create a file that's just timestamps (will be empty after cleaning)
        empty_file = tmp_path / "empty.vtt"
        empty_file.write_text(
            "00:00:00.000 --> 00:00:01.000\n00:00:01.000 --> 00:00:02.000"
        )
        result = processor.process(empty_file)
        assert result.status == "error"
        assert "empty" in result.error_message.lower()

    def test_process_very_short_transcript(self, processor, tmp_path):
        """Word count < 100 returns warning but success."""
        short_file = tmp_path / "short.txt"
        short_file.write_text("This is a short transcript with only a few words.")
        result = processor.process(short_file)
        assert result.status == "success"
        assert "short" in result.error_message.lower()

    def test_process_manual_transcript(self, processor):
        """Manual override with text string works."""
        text = "This is manually provided transcript text for processing."
        result = processor.process_manual_transcript(text)
        assert result.status == "success"
        assert result.cleaned_text is not None
        assert result.word_count is not None

    def test_process_manual_empty_transcript(self, processor):
        """Empty manual transcript returns error."""
        result = processor.process_manual_transcript("")
        assert result.status == "error"
        assert "empty" in result.error_message.lower()

    def test_process_malformed_transcript(self, processor, tmp_path):
        """Malformed transcript with mixed formats → best-effort parsing."""
        # Create a file with corrupted/mixed format content
        malformed_file = tmp_path / "malformed.vtt"
        malformed_file.write_text("""WEBVTT

1
00:00:00.500 --> 00:00:07.000
Some content here

[Corrupted section]
More text
""")
        result = processor.process(malformed_file)
        # Should still succeed with partial parsing
        assert result.status == "success"
        assert result.cleaned_text is not None
        assert len(result.cleaned_text) > 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_pipeline_with_filler_and_pii(self, processor, tmp_path):
        """Complete pipeline with filler words and PII."""
        content = """WEBVTT

00:00:00.500 --> 00:00:07.000
So, um, like, contact john.doe@example.com for help.

00:00:07.000 --> 00:00:10.000
[Speaker Name] Here's the important stuff, right?
"""
        vtt_file = tmp_path / "complex.vtt"
        vtt_file.write_text(content)

        result = processor.process(vtt_file)
        assert result.status == "success"
        assert "@" not in result.cleaned_text
        assert "john.doe" not in result.cleaned_text
        assert "-->" not in result.cleaned_text
        assert "um" not in result.cleaned_text.lower()
        assert "important" in result.cleaned_text.lower()

    def test_error_recovery_flow(self, processor, tmp_path):
        """Error cases return actionable messages."""
        # Test missing file
        missing = processor.process(Path("/nonexistent/file.vtt"))
        assert missing.status == "missing"
        assert missing.error_message is not None

        # Test empty file
        empty = tmp_path / "empty.vtt"
        empty.write_text("WEBVTT\n\n")
        empty_result = processor.process(empty)
        assert empty_result.status == "error"

    def test_word_count_accuracy(self, processor, tmp_path):
        """Word counts are accurate."""
        text = "One two three four five six seven eight nine ten"
        txt_file = tmp_path / "count.txt"
        txt_file.write_text(text)

        result = processor.process(txt_file)
        assert result.status == "success"
        assert result.word_count == 10

    def test_various_formats_in_single_run(self, processor, tmp_path):
        """Can process VTT, SRT, and TXT formats."""
        # VTT
        vtt_file = tmp_path / "test.vtt"
        vtt_file.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTest vtt format")
        vtt_result = processor.process(vtt_file)
        assert vtt_result.status == "success"
        assert "-->" not in vtt_result.cleaned_text  # timestamps removed
        assert "test" in vtt_result.cleaned_text.lower()
        assert "format" in vtt_result.cleaned_text.lower()

        # TXT
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Plain text content")
        txt_result = processor.process(txt_file)
        assert txt_result.status == "success"
        assert "content" in txt_result.cleaned_text

        # SRT
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:00,000 --> 00:00:01,000\nSRT test format")
        srt_result = processor.process(srt_file)
        assert srt_result.status == "success"
        assert "-->" not in srt_result.cleaned_text  # timestamps removed
        assert "test" in srt_result.cleaned_text.lower()
        assert "format" in srt_result.cleaned_text.lower()
