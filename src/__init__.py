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
    TranscriptError,
)
from src.audio_extractor import extract_audio, validate_audio_output
from src.transcript_processor import (
    TranscriptProcessor,
    parse_transcript,
    clean_transcript,
    strip_pii,
)

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
    "TranscriptError",
    "extract_audio",
    "validate_audio_output",
    "TranscriptProcessor",
    "parse_transcript",
    "clean_transcript",
    "strip_pii",
]
