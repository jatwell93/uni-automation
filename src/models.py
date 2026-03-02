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


@dataclass
class TranscriptResult:
    """Result of transcript processing operation."""

    status: str  # "success", "missing", "error"
    cleaned_text: Optional[str] = None
    word_count: Optional[int] = None
    original_word_count: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class AudioExtractionResult:
    """Result of an audio extraction operation."""

    status: str  # "success" or "error"
    output_path: Optional[Path] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None


class AudioExtractionError(Exception):
    """Exception raised when audio extraction fails."""

    pass


class TranscriptError(Exception):
    """Exception raised when transcript processing fails."""

    pass


@dataclass
class SlideExtractionResult:
    """Result of a slide text extraction operation."""

    status: str  # "success", "partial", "error", "missing"
    slide_text: Optional[str] = (
        None  # Organized by page: "[Page 1]\n...\n[Page 2]\n..."
    )
    page_count: Optional[int] = None
    text_pages: Optional[int] = None  # Pages with extractable text
    used_ocr: bool = False
    error_message: Optional[str] = None


class SlideExtractionError(Exception):
    """Exception raised when slide extraction fails."""

    pass


@dataclass
class LLMResult:
    """Result of an LLM generation operation."""

    status: str  # "success", "error", "truncated"
    content: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: Optional[str] = None
    cost_aud: float = 0.0


class LLMError(Exception):
    """Exception raised when LLM operations fail."""

    pass


@dataclass
class CostTrackingEntry:
    """Record of a lecture cost tracking entry."""

    lecture: str
    timestamp: str
    input_tokens: int
    output_tokens: int
    model: str
    cost_aud: float
