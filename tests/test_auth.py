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
            mock_response.json.return_value = {"id": "user123", "name": "Test User"}
            mock_get.return_value = mock_response

            result = validate_session(
                cookies=cookies,
                panopto_base_url="https://uni.panopto.com",
            )

            assert result.success is True
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

            assert result.success is False
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

            assert result.success is False
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
            # Strategy A times out
            mock_get.side_effect = requests.Timeout()

            with patch("src.auth.requests.head") as mock_head:
                # Strategy B also times out
                mock_head.side_effect = requests.Timeout()

                result = validate_session(
                    cookies=cookies,
                    panopto_base_url="https://uni.panopto.com",
                )

                assert result.success is False
                assert (
                    "timeout" in result.message.lower()
                    or "not responding" in result.message.lower()
                )

    def test_validate_session_connection_error(self):
        """Test session validation with connection error."""
        from requests.cookies import RequestsCookieJar
        import requests

        cookies = RequestsCookieJar()
        cookies.set("session_id", "abc123")

        with patch("src.auth.requests.get") as mock_get:
            # Strategy A connection error
            mock_get.side_effect = requests.ConnectionError()

            with patch("src.auth.requests.head") as mock_head:
                # Strategy B also connection error
                mock_head.side_effect = requests.ConnectionError()

                result = validate_session(
                    cookies=cookies,
                    panopto_base_url="https://uni.panopto.com",
                )

                assert result.success is False
                assert (
                    "cannot reach" in result.message.lower()
                    or "network" in result.message.lower()
                )

    def test_validate_session_strategy_b_fallback(self):
        """Test that Strategy B fallback works when Strategy A fails."""
        from requests.cookies import RequestsCookieJar

        cookies = RequestsCookieJar()
        cookies.set("session_id", "abc123")

        with patch("src.auth.requests.get") as mock_get:
            # Strategy A (GET) returns 500 error, trigger fallback
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            with patch("src.auth.requests.head") as mock_head:
                # Strategy B (HEAD) succeeds with 200
                mock_head_response = Mock()
                mock_head_response.status_code = 200
                mock_head.return_value = mock_head_response

                result = validate_session(
                    cookies=cookies,
                    panopto_base_url="https://uni.panopto.com",
                )

                assert result.success is True
                assert mock_head.called  # Verify fallback was used


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
