"""Tests for the auth module."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.auth import load_cookies, validate_session, AuthResult, SessionInfo


class TestLoadCookies:
    """Tests for load_cookies function."""

    def test_load_cookies_success(self):
        """Test successful cookie loading from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.json"

            # Create valid cookie JSON
            cookies_data = [
                {
                    "name": "session_id",
                    "value": "abc123",
                    "domain": "uni.panopto.com",
                    "path": "/",
                },
                {
                    "name": "auth_token",
                    "value": "def456",
                    "domain": "uni.panopto.com",
                    "path": "/",
                },
            ]

            with open(cookie_file, "w") as f:
                json.dump(cookies_data, f)

            jar = load_cookies(cookie_file)

            assert len(jar) == 2
            assert jar.get("session_id") == "abc123"
            assert jar.get("auth_token") == "def456"

    def test_load_cookies_file_not_found(self):
        """Test error when cookie file not found."""
        with pytest.raises(FileNotFoundError):
            load_cookies("/nonexistent/cookies.json")

    def test_load_cookies_invalid_json(self):
        """Test error with invalid JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.json"

            # Write invalid JSON
            with open(cookie_file, "w") as f:
                f.write("not valid json {")

            with pytest.raises(json.JSONDecodeError):
                load_cookies(cookie_file)

    def test_load_cookies_missing_required_fields(self):
        """Test error with missing required cookie fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.json"

            # Cookie missing 'value' field
            cookies_data = [
                {
                    "name": "session_id",
                    # Missing 'value' field
                    "domain": "uni.panopto.com",
                },
            ]

            with open(cookie_file, "w") as f:
                json.dump(cookies_data, f)

            with pytest.raises(ValueError):
                load_cookies(cookie_file)

    def test_load_cookies_not_array(self):
        """Test error when JSON is not an array."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookie_file = Path(tmpdir) / "cookies.json"

            # JSON object instead of array
            cookies_data = {"name": "session_id", "value": "abc123"}

            with open(cookie_file, "w") as f:
                json.dump(cookies_data, f)

            with pytest.raises(ValueError):
                load_cookies(cookie_file)


class TestValidateSession:
    """Tests for validate_session function."""

    def test_validate_session_success(self):
        """Test successful session validation."""
        from requests.cookies import RequestsCookieJar

        cookies = RequestsCookieJar()
        cookies.set("session_id", "abc123")

        with patch("src.auth.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = validate_session(
                cookies=cookies,
                panopto_base_url="https://uni.panopto.com",
            )

            assert result.valid is True
            assert "valid" in result.message.lower()

    def test_validate_session_unauthorized(self):
        """Test session validation with expired cookies (401)."""
        from requests.cookies import RequestsCookieJar

        cookies = RequestsCookieJar()
        cookies.set("session_id", "expired")

        with patch("src.auth.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            result = validate_session(
                cookies=cookies,
                panopto_base_url="https://uni.panopto.com",
            )

            assert result.valid is False
            assert (
                "expired" in result.message.lower()
                or "invalid" in result.message.lower()
            )

    def test_validate_session_forbidden(self):
        """Test session validation with forbidden access (403)."""
        from requests.cookies import RequestsCookieJar

        cookies = RequestsCookieJar()
        cookies.set("session_id", "abc123")

        with patch("src.auth.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_get.return_value = mock_response

            result = validate_session(
                cookies=cookies,
                panopto_base_url="https://uni.panopto.com",
            )

            assert result.valid is False
            assert (
                "access" in result.message.lower() or "denied" in result.message.lower()
            )

    def test_validate_session_timeout(self):
        """Test session validation timeout."""
        from requests.cookies import RequestsCookieJar
        import requests

        cookies = RequestsCookieJar()
        cookies.set("session_id", "abc123")

        with patch("src.auth.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout()

            result = validate_session(
                cookies=cookies,
                panopto_base_url="https://uni.panopto.com",
            )

            assert result.valid is False
            assert "timeout" in result.message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
