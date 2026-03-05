"""Tests for URL fetching and conversion module."""

import pytest
import requests as req
from pathlib import Path
from unittest.mock import patch, Mock

from src.url_fetcher import url_to_filename, fetch_url_to_file


class TestUrlToFilename:
    def test_ibm_article(self):
        url = "https://www.ibm.com/think/topics/olap-vs-oltp"
        result = url_to_filename(url)
        assert result.startswith("reading_")
        assert result.endswith(".md")
        assert "ibm" in result
        assert "olap" in result

    def test_strips_www(self):
        result = url_to_filename("https://www.example.com/article")
        assert result == "reading_example.com_article.md"
        assert "www" not in result

    def test_simple_url(self):
        result = url_to_filename("https://example.com/article")
        assert result == "reading_example.com_article.md"

    def test_no_path(self):
        result = url_to_filename("https://example.com")
        assert result == "reading_example.com.md"

    def test_truncates_long_url(self):
        long_url = "https://example.com/" + "a" * 200
        result = url_to_filename(long_url)
        # reading_ (8) + name (<=120) + .md (3) = <=131
        assert len(result) <= 131

    def test_special_chars_replaced(self):
        result = url_to_filename("https://example.com/foo?bar=baz&x=1")
        assert " " not in result
        assert "?" not in result
        assert "=" not in result
        assert "&" not in result


class TestFetchUrlToFile:
    SAMPLE_HTML = "<html><body><h1>Hello World</h1><p>Some content here.</p></body></html>"

    def test_successful_fetch_writes_markdown(self, tmp_path):
        dest = tmp_path / "reading_test.md"
        mock_resp = Mock(text=self.SAMPLE_HTML)
        mock_resp.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_resp):
            result = fetch_url_to_file("https://example.com", dest)

        assert result is True
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert "Hello World" in content

    def test_cached_file_skips_network(self, tmp_path):
        dest = tmp_path / "reading_cached.md"
        dest.write_text("cached content", encoding="utf-8")

        with patch("requests.get") as mock_get:
            result = fetch_url_to_file("https://example.com", dest)

        assert result is True
        mock_get.assert_not_called()
        # cached content untouched
        assert dest.read_text(encoding="utf-8") == "cached content"

    def test_connection_error_returns_false(self, tmp_path):
        dest = tmp_path / "reading_fail.md"

        with patch("requests.get", side_effect=req.ConnectionError("offline")):
            result = fetch_url_to_file("https://example.com", dest)

        assert result is False
        assert not dest.exists()

    def test_http_error_returns_false(self, tmp_path):
        dest = tmp_path / "reading_404.md"
        mock_resp = Mock(text="")
        mock_resp.raise_for_status.side_effect = req.HTTPError("404 Not Found")

        with patch("requests.get", return_value=mock_resp):
            result = fetch_url_to_file("https://example.com/missing", dest)

        assert result is False
        assert not dest.exists()

    def test_empty_converted_content_returns_false(self, tmp_path):
        dest = tmp_path / "reading_empty.md"
        # HTML that produces empty markdown after conversion
        mock_resp = Mock(text="<html><body></body></html>")
        mock_resp.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_resp):
            result = fetch_url_to_file("https://example.com/empty", dest)

        assert result is False
        assert not dest.exists()

    def test_timeout_returns_false(self, tmp_path):
        dest = tmp_path / "reading_timeout.md"

        with patch("requests.get", side_effect=req.Timeout("timed out")):
            result = fetch_url_to_file("https://example.com", dest)

        assert result is False

    def test_missing_parent_directory_returns_false(self, tmp_path):
        dest = tmp_path / "nonexistent_dir" / "reading_test.md"
        mock_resp = Mock(text=self.SAMPLE_HTML)
        mock_resp.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_resp):
            result = fetch_url_to_file("https://example.com", dest)

        assert result is False
        assert not dest.exists()
