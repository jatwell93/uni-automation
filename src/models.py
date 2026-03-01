"""Data models for configuration, authentication, download, and validation operations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class SessionInfo:
    """Information about the authenticated session."""

    user_id: Optional[str] = None
    username: Optional[str] = None
    expires_at: Optional[str] = None


@dataclass
class AuthResult:
    """Result of authentication operation."""

    success: bool
    message: str
    session_info: Optional[SessionInfo] = None
    expires_in_seconds: Optional[int] = None


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    message: str = ""
    error: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    success: bool
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    codec_name: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


@dataclass
class TranscriptInfo:
    """Information about a transcript file."""

    success: bool
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    format: Optional[str] = None  # "vtt", "srt", "txt", "json"
    message: str = ""


# Alias for compatibility
TranscriptResult = TranscriptInfo
