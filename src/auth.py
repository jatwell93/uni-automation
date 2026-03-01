"""Panopto authentication using browser cookies."""

import json
import logging
from pathlib import Path
from typing import Optional

import requests
from requests.cookies import RequestsCookieJar

logger = logging.getLogger(__name__)


class AuthResult:
    """Result of authentication operation."""

    def __init__(self, success: bool, message: str = "", error: Optional[str] = None):
        self.success = success
        self.message = message
        self.error = error


class SessionInfo:
    """Information about the authenticated session."""

    def __init__(
        self, valid: bool, expires_in_days: Optional[int] = None, message: str = ""
    ):
        self.valid = valid
        self.expires_in_days = expires_in_days
        self.message = message


def load_cookies(cookie_file: str | Path) -> RequestsCookieJar:
    """
    Load browser cookies from JSON export file.

    Supports Chrome, Firefox, and Edge JSON export formats.

    Args:
        cookie_file: Path to browser cookie JSON file

    Returns:
        RequestsCookieJar with loaded cookies

    Raises:
        FileNotFoundError: Cookie file not found
        json.JSONDecodeError: Invalid JSON format
        ValueError: Missing required cookie fields
    """
    cookie_file = Path(cookie_file)

    try:
        with open(cookie_file, "r") as f:
            cookie_data = json.load(f)

        if not isinstance(cookie_data, list):
            raise ValueError("Cookie file must contain an array of cookie objects")

        # Create cookie jar
        jar = RequestsCookieJar()

        for cookie_dict in cookie_data:
            # Validate required fields
            if "name" not in cookie_dict or "value" not in cookie_dict:
                raise ValueError("Cookie object missing required fields: name, value")

            # Extract cookie attributes
            name = cookie_dict["name"]
            value = cookie_dict["value"]
            domain = cookie_dict.get("domain", "")
            path = cookie_dict.get("path", "/")

            # Add to cookie jar
            jar.set(
                name=name,
                value=value,
                domain=domain,
                path=path,
            )

        logger.info(f"✓ Loaded {len(jar)} cookies from {cookie_file.name}")
        return jar

    except FileNotFoundError:
        error_msg = (
            f"Cookie file not found: {cookie_file}\n"
            "To extract cookies from your browser:\n"
            "1. Chrome/Edge: DevTools → Application → Cookies → Right-click → Export as JSON\n"
            "2. Firefox: Use Cookie Editor extension → Export as JSON\n"
            "3. Any browser: Use Cookie Editor Chrome extension"
        )
        logger.error(error_msg)
        raise

    except json.JSONDecodeError as e:
        error_msg = (
            f"Cookie file is not valid JSON: {cookie_file}\n"
            f"JSON error: {str(e)}\n"
            "Check file format or re-export from browser"
        )
        logger.error(error_msg)
        raise

    except ValueError as e:
        error_msg = (
            f"Cookie file format error: {str(e)}\n"
            "File must contain array of objects with 'name' and 'value' fields"
        )
        logger.error(error_msg)
        raise


def validate_session(
    cookies: RequestsCookieJar,
    panopto_base_url: str,
) -> SessionInfo:
    """
    Validate that authentication cookies are fresh and working.

    Tests API call to Panopto before attempting download.

    Args:
        cookies: Authenticated cookie jar from load_cookies()
        panopto_base_url: Base URL of Panopto instance (e.g., https://uni.panopto.com)

    Returns:
        SessionInfo with validity status and expiry info
    """
    try:
        # Make test API call to validate cookies
        test_url = f"{panopto_base_url}/api/v1/me"  # Simple endpoint to test auth

        response = requests.get(
            test_url,
            cookies=cookies,
            timeout=10,
        )

        if response.status_code == 401:
            error_msg = (
                "Cookies expired or invalid. Refresh from browser:\n"
                "1. Open Panopto in your browser\n"
                "2. Re-export cookies\n"
                "3. Update cookie file path in config"
            )
            logger.error(error_msg)
            return SessionInfo(valid=False, expires_in_days=None, message=error_msg)

        if response.status_code == 403:
            error_msg = (
                "Access denied. Check that cookies are from the correct account."
            )
            logger.error(error_msg)
            return SessionInfo(valid=False, expires_in_days=None, message=error_msg)

        if response.status_code >= 400:
            error_msg = f"Session validation failed (HTTP {response.status_code}). Cookies may be invalid."
            logger.error(error_msg)
            return SessionInfo(valid=False, expires_in_days=None, message=error_msg)

        # Session is valid
        # Estimate expiry (try to extract from cookies if available)
        expires_in_days = None
        for cookie in cookies:
            if cookie.expires:
                # Calculate days until expiry (rough estimate)
                import time

                expires_in_days = max(0, (cookie.expires - int(time.time())) // 86400)
                break

        success_msg = f"✓ Session valid"
        if expires_in_days:
            success_msg += f" (expires in {expires_in_days} days)"

        logger.info(success_msg)
        return SessionInfo(
            valid=True, expires_in_days=expires_in_days, message=success_msg
        )

    except requests.Timeout:
        error_msg = "Session validation timeout. Check internet connection."
        logger.error(error_msg)
        return SessionInfo(valid=False, message=error_msg)

    except requests.ConnectionError:
        error_msg = "Cannot reach Panopto. Check URL and network connection."
        logger.error(error_msg)
        return SessionInfo(valid=False, message=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error validating session: {str(e)}"
        logger.error(error_msg)
        return SessionInfo(valid=False, message=error_msg)
