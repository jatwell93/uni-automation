"""Tests for the downloader module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from requests.cookies import RequestsCookieJar

from src.downloader import (
    download_video,
    download_transcript,
    extract_session_id,
    extract_base_url,
)
from src.models import DownloadResult, TranscriptInfo


class TestDownloadVideo:
    """Tests for download_video function."""

    def test_download_video_success(self):
        """Test successful video download with streaming."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video.mp4"

            # Mock the requests.get call
            with patch("src.downloader.requests.get") as mock_get:
                # Create mock response
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.iter_content = Mock(return_value=[b"chunk1", b"chunk2"])
                mock_get.return_value = mock_response

                # Create a test file to verify writing
                result = download_video(
                    video_url="https://example.panopto.com/video",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                    timeout=300,
                )

                # Verify result structure
                assert result.success is True
                assert result.error is None
                assert "Downloaded" in result.message

    def test_download_video_timeout(self):
        """Test download timeout with cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video.mp4"

            # Mock timeout
            with patch("src.downloader.requests.get") as mock_get:
                mock_get.side_effect = Exception("timeout")

                result = download_video(
                    video_url="https://example.panopto.com/video",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                )

                assert result.success is False
                assert result.error is not None

    def test_download_video_404_error(self):
        """Test 404 error handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video.mp4"

            with patch("src.downloader.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 404
                mock_get.return_value = mock_response

                result = download_video(
                    video_url="https://example.panopto.com/nonexistent",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                )

                assert result.success is False
                assert "not found" in result.error.lower()

    def test_download_video_403_forbidden(self):
        """Test 403 forbidden error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video.mp4"

            with patch("src.downloader.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 403
                mock_get.return_value = mock_response

                result = download_video(
                    video_url="https://example.panopto.com/video",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                )

                assert result.success is False
                assert (
                    "denied" in result.error.lower() or "access" in result.error.lower()
                )

    def test_download_video_cleanup_on_error(self):
        """Test that partial files are cleaned up on error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video.mp4"

            with patch("src.downloader.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.iter_content = Mock(side_effect=IOError("Disk error"))
                mock_get.return_value = mock_response

                result = download_video(
                    video_url="https://example.panopto.com/video",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                )

                assert result.success is False
                # File should be cleaned up
                assert not output_path.exists()


class TestDownloadTranscript:
    """Tests for download_transcript function."""

    def test_download_transcript_success(self):
        """Test successful transcript download."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "transcript.vtt"

            with patch("src.downloader.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {"Content-Type": "text/vtt"}
                mock_response.text = (
                    "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nTest transcript"
                )
                mock_get.return_value = mock_response

                result = download_transcript(
                    session_id="abc123",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                    panopto_base_url="https://example.panopto.com",
                )

                assert result.success is True
                assert result.file_path is not None
                assert "vtt" in result.format.lower()

    def test_download_transcript_not_available(self):
        """Test graceful skip when transcript not available (404)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "transcript.vtt"

            with patch("src.downloader.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 404
                mock_get.return_value = mock_response

                result = download_transcript(
                    session_id="abc123",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                    panopto_base_url="https://example.panopto.com",
                )

                assert result.success is False
                assert "not available" in result.message.lower()

    def test_download_transcript_timeout(self):
        """Test graceful skip on timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "transcript.vtt"

            with patch("src.downloader.requests.get") as mock_get:
                import requests

                mock_get.side_effect = requests.Timeout("timeout")

                result = download_transcript(
                    session_id="abc123",
                    output_path=output_path,
                    cookies=RequestsCookieJar(),
                    panopto_base_url="https://example.panopto.com",
                )

                assert result.success is False
                # Should not raise, should gracefully skip
                assert (
                    "timeout" in result.message.lower()
                    or "unavailable" in result.message.lower()
                )


class TestUrlParsing:
    """Tests for URL parsing utility functions."""

    def test_extract_session_id_from_url(self):
        """Test extracting session ID from Panopto URL."""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123def456&other=param"
        session_id = extract_session_id(url)
        assert session_id == "abc123def456"

    def test_extract_session_id_no_id_param(self):
        """Test handling URL without id parameter."""
        url = "https://uni.panopto.com/Panopto/Pages/Sessions/List.aspx?course=test"
        session_id = extract_session_id(url)
        assert session_id == ""  # Should return empty string

    def test_extract_base_url(self):
        """Test extracting base URL from Panopto URL."""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
        base_url = extract_base_url(url)
        assert base_url == "https://uni.panopto.com"

    def test_extract_base_url_with_port(self):
        """Test extracting base URL with custom port."""
        url = "https://uni.panopto.com:8080/Panopto/Pages/Viewer.aspx?id=abc123"
        base_url = extract_base_url(url)
        assert base_url == "https://uni.panopto.com:8080"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
