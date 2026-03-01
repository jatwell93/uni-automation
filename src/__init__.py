"""Uni automation package - lecture processing pipeline."""

from src.config import ConfigModel, load_config
from src.models import (
    SessionInfo,
    AuthResult,
    DownloadResult,
    ValidationResult,
    TranscriptInfo,
    TranscriptResult,
    AudioExtractionResult,
    AudioExtractionError,
)
from src.audio_extractor import extract_audio, validate_audio_output

__all__ = [
    "ConfigModel",
    "load_config",
    "SessionInfo",
    "AuthResult",
    "DownloadResult",
    "ValidationResult",
    "TranscriptInfo",
    "TranscriptResult",
    "AudioExtractionResult",
    "AudioExtractionError",
    "extract_audio",
    "validate_audio_output",
]
