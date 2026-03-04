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
    SlideExtractionResult,
    SlideExtractionError,
)
from src.audio_extractor import extract_audio, validate_audio_output
from src.transcript_processor import (
    TranscriptProcessor,
    parse_transcript,
    clean_transcript,
    strip_pii,
)
from src.slide_extractor import (
    SlideExtractor,
    extract_slide_text,
    detect_image_slides,
)
from dotenv import load_dotenv

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
    "SlideExtractionResult",
    "SlideExtractionError",
    "extract_audio",
    "validate_audio_output",
    "TranscriptProcessor",
    "parse_transcript",
    "clean_transcript",
    "strip_pii",
    "SlideExtractor",
    "extract_slide_text",
    "detect_image_slides",
]
