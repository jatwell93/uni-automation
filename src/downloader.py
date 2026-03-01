"""Video and transcript download module with streaming and cleanup."""

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.cookies import RequestsCookieJar

from src.models import DownloadResult, TranscriptInfo

logger = logging.getLogger(__name__)


def download_video(
    video_url: str,
    output_path: str | Path,
    cookies: RequestsCookieJar,
    timeout: int = 300,
) -> DownloadResult:
    """
    Download a video file using streaming to avoid memory bloat.

    Args:
        video_url: URL of the video to download
        output_path: Local path to save the video
        cookies: Authenticated cookie jar for Panopto
        timeout: Timeout in seconds (default 300 for large files)

    Returns:
        DownloadResult with success status, file path, and size
    """
    output_path = Path(output_path)

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading video from {video_url}...")

        # Make streaming request
        response = requests.get(
            video_url,
            cookies=cookies,
            stream=True,
            timeout=timeout,
        )

        # Handle HTTP errors
        if response.status_code == 404:
            error_msg = (
                f"Video not found at URL: {video_url}. Check Panopto URL in config."
            )
            logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )
        elif response.status_code == 403:
            error_msg = (
                "Access denied. Check that cookies are fresh and from correct account."
            )
            logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )
        elif response.status_code < 200 or response.status_code >= 300:
            error_msg = f"HTTP {response.status_code}: Cannot download video. Check URL and network."
            logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )

        # Stream download in chunks
        bytes_downloaded = 0
        chunk_size = 8192  # 8KB chunks

        try:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        # Log progress every 50MB
                        if bytes_downloaded % (50 * 1024 * 1024) == 0:
                            mb_downloaded = bytes_downloaded / (1024 * 1024)
                            logger.debug(f"Downloaded {mb_downloaded:.1f}MB...")

            # Verify file was written
            if not output_path.exists():
                error_msg = "Download completed but file not found on disk."
                logger.error(error_msg)
                return DownloadResult(
                    success=False,
                    error=error_msg,
                    message=error_msg,
                )

            file_size = output_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            success_msg = f"✓ Downloaded {output_path.name} ({file_size_mb:.1f}MB)"
            logger.info(success_msg)

            return DownloadResult(
                success=True,
                file_path=output_path,
                file_size=file_size,
                message=success_msg,
            )

        except IOError as e:
            if "disk" in str(e).lower():
                error_msg = (
                    "Not enough disk space for download. Free up space and retry."
                )
            elif "permission" in str(e).lower():
                error_msg = f"Cannot write to output directory: {output_path}. Check permissions."
            else:
                error_msg = f"Error writing download: {str(e)}"

            logger.error(error_msg)
            logger.info(f"Cleaning up partial file: {output_path}")

            try:
                output_path.unlink(missing_ok=True)
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup partial file: {cleanup_err}")

            return DownloadResult(
                success=False,
                error=error_msg,
                message=error_msg,
            )

    except requests.Timeout:
        error_msg = "Download timeout. Check internet connection and try again. Partial file deleted."
        logger.error(error_msg)

        try:
            output_path.unlink(missing_ok=True)
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup partial file: {cleanup_err}")

        return DownloadResult(
            success=False,
            error=error_msg,
            message=error_msg,
        )

    except requests.ConnectionError:
        error_msg = "Cannot reach Panopto. Check URL and network connection."
        logger.error(error_msg)

        try:
            output_path.unlink(missing_ok=True)
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup partial file: {cleanup_err}")

        return DownloadResult(
            success=False,
            error=error_msg,
            message=error_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during download: {str(e)}"
        logger.error(error_msg)

        try:
            output_path.unlink(missing_ok=True)
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup partial file: {cleanup_err}")

        return DownloadResult(
            success=False,
            error=error_msg,
            message=error_msg,
        )


def extract_session_id(panopto_url: str) -> str:
    """
    Extract session ID from Panopto URL.

    Typical formats:
    - https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123def
    - https://uni.panopto.com/Panopto/Pages/Sessions/List.aspx?...

    Args:
        panopto_url: Full Panopto URL

    Returns:
        Session ID (the 'id' parameter from the URL)
    """
    parsed = urlparse(panopto_url)
    params = parsed.query.split("&")

    for param in params:
        if param.startswith("id="):
            return param.split("=", 1)[1]

    # Fallback: if no id parameter, try to extract from path
    # Some URLs might have the ID in a different format
    return ""


def extract_base_url(panopto_url: str) -> str:
    """
    Extract base URL from Panopto URL.

    Args:
        panopto_url: Full Panopto URL

    Returns:
        Base URL (scheme + netloc, e.g., https://uni.panopto.com)
    """
    parsed = urlparse(panopto_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def download_transcript(
    session_id: str,
    output_path: str | Path,
    cookies: RequestsCookieJar,
    panopto_base_url: str,
) -> TranscriptInfo:
    """
    Download transcript from Panopto API (optional, graceful failure).

    Args:
        session_id: Panopto session ID
        output_path: Local path to save the transcript
        cookies: Authenticated cookie jar for Panopto
        panopto_base_url: Base URL of Panopto instance

    Returns:
        TranscriptInfo with success status or graceful failure
    """
    output_path = Path(output_path)

    try:
        logger.info("Attempting to download transcript...")

        # Try to fetch transcript via API
        # Note: Exact endpoint may vary; this is a common pattern
        transcript_url = f"{panopto_base_url}/api/v1/sessions/{session_id}/transcript"

        response = requests.get(
            transcript_url,
            cookies=cookies,
            timeout=30,
        )

        # Gracefully skip if transcript not available
        if response.status_code == 404:
            logger.warning(
                "Transcript not available (404). Proceeding with video only."
            )
            return TranscriptInfo(
                success=False,
                message="Transcript not available; proceeding with video only",
            )

        if response.status_code == 403:
            logger.warning(
                "Cannot access transcript (403). Proceeding with video only."
            )
            return TranscriptInfo(
                success=False,
                message="Transcript access denied; proceeding with video only",
            )

        if response.status_code < 200 or response.status_code >= 300:
            logger.warning(
                f"Transcript fetch failed with HTTP {response.status_code}. Skipping."
            )
            return TranscriptInfo(
                success=False,
                message=f"Transcript unavailable (HTTP {response.status_code})",
            )

        # Determine format from Content-Type or file extension
        content_type = response.headers.get("Content-Type", "text/plain")
        if "vtt" in content_type.lower():
            transcript_format = "vtt"
        elif "srt" in content_type.lower():
            transcript_format = "srt"
        elif "json" in content_type.lower():
            transcript_format = "json"
        else:
            # Default based on response content
            if response.text.startswith("WEBVTT"):
                transcript_format = "vtt"
            else:
                transcript_format = "txt"

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write transcript with UTF-8 encoding
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(response.text)

        file_size = output_path.stat().st_size

        success_msg = (
            f"✓ Downloaded transcript ({transcript_format}, {file_size} bytes)"
        )
        logger.info(success_msg)

        return TranscriptInfo(
            success=True,
            file_path=output_path,
            file_size=file_size,
            format=transcript_format,
            message=success_msg,
        )

    except requests.Timeout:
        logger.warning(
            "Transcript download timeout. Skipping transcript; video available."
        )
        return TranscriptInfo(
            success=False,
            message="Transcript download timeout; proceeding with video only",
        )

    except requests.ConnectionError:
        logger.warning("Cannot reach Panopto API. Skipping transcript.")
        return TranscriptInfo(
            success=False,
            message="Transcript API unavailable; proceeding with video only",
        )

    except IOError as e:
        if "disk" in str(e).lower():
            logger.warning("Disk full when downloading transcript. Skipping.")
        else:
            logger.warning(f"Error writing transcript: {str(e)}. Skipping.")

        return TranscriptInfo(
            success=False,
            message="Failed to write transcript; proceeding with video only",
        )

    except Exception as e:
        logger.warning(f"Unexpected error downloading transcript: {str(e)}. Skipping.")
        return TranscriptInfo(
            success=False,
            message="Unexpected transcript error; proceeding with video only",
        )
