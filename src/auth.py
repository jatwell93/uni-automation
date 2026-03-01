"""Panopto authentication using browser cookies."""

import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests
from requests.cookies import RequestsCookieJar

from src.models import AuthResult, SessionInfo

logger = logging.getLogger(__name__)


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
) -> AuthResult:
    """
    Validate that authentication cookies are fresh and working.

    Tests API call to Panopto before attempting download. Uses Strategy A
    (GET /api/v1/user/me) as preferred, with Strategy B (HEAD request) as fallback.

    Args:
        cookies: Authenticated cookie jar from load_cookies()
        panopto_base_url: Base URL of Panopto instance (e.g., https://uni.panopto.com)

    Returns:
        AuthResult with success status, message, and optional session info
    """
    try:
        # Strategy A (preferred): GET /api/v1/user/me
        test_url = f"{panopto_base_url}/api/v1/user/me"
        logger.debug(f"Attempting Strategy A: GET {test_url}")

        try:
            response = requests.get(
                test_url,
                cookies=cookies,
                timeout=10,
            )

            if response.status_code == 401:
                error_msg = (
                    "Cookies expired or invalid. Refresh from browser:\n"
                    "1. Open {}\n"
                    "2. DevTools (F12) → Storage → Cookies\n"
                    "3. Export as JSON\n"
                    "4. Save to cookie file\n"
                    "5. Re-run: python run_week.py <config_file>"
                ).format(panopto_base_url)
                logger.error(error_msg)
                return AuthResult(success=False, message=error_msg)

            if response.status_code == 403:
                error_msg = "Access denied. Check that cookies are from correct institution/account."
                logger.error(error_msg)
                return AuthResult(success=False, message=error_msg)

            if response.status_code >= 400:
                # Strategy A failed, try Strategy B
                logger.warning(
                    f"Strategy A failed with {response.status_code}, trying Strategy B"
                )
                return _validate_session_strategy_b(cookies, panopto_base_url)

            # Strategy A succeeded - extract session info if available
            expires_in_seconds = _calculate_expiry(cookies)
            session_info = _extract_session_info(response)

            success_msg = "✓ Session valid"
            if expires_in_seconds:
                days = expires_in_seconds // 86400
                success_msg += f" (expires in {days} days)"

            logger.info(success_msg)
            return AuthResult(
                success=True,
                message=success_msg,
                session_info=session_info,
                expires_in_seconds=expires_in_seconds,
            )

        except requests.Timeout:
            logger.warning("Strategy A timeout, trying Strategy B")
            return _validate_session_strategy_b(cookies, panopto_base_url)

        except requests.ConnectionError:
            logger.warning("Strategy A connection error, trying Strategy B")
            return _validate_session_strategy_b(cookies, panopto_base_url)

    except requests.Timeout:
        error_msg = (
            "Panopto API not responding. Check internet connection and try again."
        )
        logger.error(error_msg)
        return AuthResult(success=False, message=error_msg)

    except requests.ConnectionError:
        error_msg = f"Cannot reach Panopto. Check URL or network connection.\nURL: {panopto_base_url}"
        logger.error(error_msg)
        return AuthResult(success=False, message=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error validating session: {str(e)}"
        logger.error(error_msg)
        return AuthResult(success=False, message=error_msg)


def _validate_session_strategy_b(
    cookies: RequestsCookieJar,
    panopto_base_url: str,
) -> AuthResult:
    """
    Strategy B fallback: HEAD request to base URL.

    When Strategy A (detailed API call) fails, try a minimal HEAD request
    to verify basic connectivity and authentication.

    Args:
        cookies: Authenticated cookie jar
        panopto_base_url: Base URL of Panopto instance

    Returns:
        AuthResult based on HEAD request response
    """
    try:
        logger.debug(f"Attempting Strategy B: HEAD {panopto_base_url}")

        response = requests.head(
            panopto_base_url,
            cookies=cookies,
            timeout=10,
        )

        if response.status_code == 401:
            error_msg = (
                "Cookies expired or invalid. Refresh from browser:\n"
                "1. Open {}\n"
                "2. DevTools (F12) → Storage → Cookies\n"
                "3. Export as JSON\n"
                "4. Save to cookie file\n"
                "5. Re-run: python run_week.py <config_file>"
            ).format(panopto_base_url)
            logger.error(error_msg)
            return AuthResult(success=False, message=error_msg)

        if response.status_code == 403:
            error_msg = "Access denied. Check that cookies are from correct institution/account."
            logger.error(error_msg)
            return AuthResult(success=False, message=error_msg)

        if response.status_code >= 400:
            error_msg = f"Panopto returned {response.status_code}. Try refreshing cookies and re-running."
            logger.error(error_msg)
            return AuthResult(success=False, message=error_msg)

        # Strategy B succeeded
        expires_in_seconds = _calculate_expiry(cookies)
        success_msg = "✓ Session valid (basic validation)"
        if expires_in_seconds:
            days = expires_in_seconds // 86400
            success_msg += f" (expires in {days} days)"

        logger.info(success_msg)
        return AuthResult(
            success=True,
            message=success_msg,
            expires_in_seconds=expires_in_seconds,
        )

    except requests.Timeout:
        error_msg = (
            "Panopto API not responding. Check internet connection and try again."
        )
        logger.error(error_msg)
        return AuthResult(success=False, message=error_msg)

    except requests.ConnectionError:
        error_msg = f"Cannot reach Panopto. Check URL or network connection.\nURL: {panopto_base_url}"
        logger.error(error_msg)
        return AuthResult(success=False, message=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error validating session: {str(e)}"
        logger.error(error_msg)
        return AuthResult(success=False, message=error_msg)


def _calculate_expiry(cookies: RequestsCookieJar) -> Optional[int]:
    """
    Calculate seconds until session expires.

    Args:
        cookies: Cookie jar to check

    Returns:
        Seconds until expiry, or None if not available
    """
    for cookie in cookies:
        if cookie.expires:
            expires_in_seconds = max(0, cookie.expires - int(time.time()))
            return expires_in_seconds
    return None


def _extract_session_info(response: requests.Response) -> Optional[SessionInfo]:
    """
    Extract session info from API response.

    Args:
        response: Response from Panopto API

    Returns:
        SessionInfo object, or None if not available
    """
    try:
        data = response.json()
        return SessionInfo(
            user_id=data.get("id"),
            username=data.get("name"),
            expires_at=data.get("expiresAt"),
        )
    except (json.JSONDecodeError, ValueError):
        # API response not JSON or missing expected fields
        return None
