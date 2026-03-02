"""Configuration management using Pydantic and YAML."""

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator, ValidationError

logger = logging.getLogger(__name__)


class LectureConfig(BaseModel):
    """Lecture-specific configuration."""

    url: str
    slide_path: str


class PathsConfig(BaseModel):
    """File paths configuration."""

    cookie_file: str
    output_dir: str


class MetadataConfig(BaseModel):
    """Optional metadata."""

    course_name: str = "Unknown Course"
    week_number: int = 1
    lecturer_name: str = ""
    timestamp: Optional[str] = None


class ConfigModel(BaseModel):
    """Main configuration model."""

    lecture: LectureConfig
    paths: PathsConfig
    metadata: MetadataConfig = MetadataConfig()
    obsidian_vault_path: str = ""
    obsidian_note_subfolder: str = "Lectures"
    openrouter_api_key: str = ""
    llm_model: str = "deepseek/deepseek-chat"
    llm_budget_aud: float = 0.30
    llm_safety_buffer: float = 0.20
    remove_pii_from_transcript: bool = True
    gdrive_sync_enabled: bool = False
    gdrive_sync_folder: Optional[str] = None

    @field_validator("lecture", mode="before")
    @classmethod
    def validate_lecture(cls, v):
        """Validate lecture configuration."""
        if isinstance(v, dict):
            # Validate URL
            url = v.get("url")
            if not url:
                raise ValueError("lecture.url is required")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(f"Invalid URL: {url}. Must be https://...")

            # Validate slide_path exists
            slide_path = v.get("slide_path")
            if slide_path and not Path(slide_path).exists():
                raise ValueError(f"Slide path does not exist: {slide_path}")
        return v

    @field_validator("paths", mode="before")
    @classmethod
    def validate_paths(cls, v):
        """Validate paths configuration."""
        if isinstance(v, dict):
            output_dir = v.get("output_dir")
            if not output_dir:
                raise ValueError("paths.output_dir is required")

            # Test if output_dir is writable
            try:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Output directory is not writable: {output_dir}. Error: {e}"
                )
        return v

    @field_validator("obsidian_vault_path", mode="before")
    @classmethod
    def validate_obsidian_vault_path(cls, v):
        """Validate obsidian vault path."""
        if isinstance(v, str) and v:
            if not v.strip():
                raise ValueError("obsidian_vault_path cannot be empty string")
        return v

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def validate_openrouter_api_key(cls, v):
        """Validate OpenRouter API key."""
        if isinstance(v, str) and v:
            if not v.strip():
                raise ValueError("openrouter_api_key cannot be empty string")
            if len(v) < 20:
                logger.warning(
                    f"openrouter_api_key seems short ({len(v)} chars), may be invalid"
                )
        return v

    @field_validator("llm_budget_aud", mode="before")
    @classmethod
    def validate_llm_budget_aud(cls, v):
        """Validate LLM budget."""
        if isinstance(v, (int, float)):
            if not (0.01 <= v <= 1.00):
                raise ValueError(
                    f"llm_budget_aud must be between 0.01 and 1.00, got {v}"
                )
        return v

    @field_validator("llm_safety_buffer", mode="before")
    @classmethod
    def validate_llm_safety_buffer(cls, v):
        """Validate LLM safety buffer."""
        if isinstance(v, (int, float)):
            if not (0.0 <= v <= 0.5):
                raise ValueError(
                    f"llm_safety_buffer must be between 0.0 and 0.5, got {v}"
                )
        return v

    @field_validator("gdrive_sync_folder", mode="before")
    @classmethod
    def validate_gdrive_sync_folder(cls, v):
        """Validate Google Drive sync folder path."""
        if isinstance(v, str) and v:
            if not v.strip():
                raise ValueError("gdrive_sync_folder cannot be empty string")
        return v

    def validate_gdrive_config(self):
        """
        Validate Google Drive sync configuration.

        If gdrive_sync_enabled=True, folder must be set and valid.
        """
        if self.gdrive_sync_enabled:
            if not self.gdrive_sync_folder:
                raise ValueError(
                    "Google Drive sync enabled but folder path not set. "
                    "Set gdrive_sync_folder or disable with gdrive_sync_enabled=false"
                )

            folder_path = Path(self.gdrive_sync_folder)

            # Check folder exists
            if not folder_path.exists():
                raise ValueError(
                    f"Google Drive sync folder not found: {self.gdrive_sync_folder}. "
                    "Verify path or disable sync with gdrive_sync_enabled=false"
                )

            # Check folder is a directory
            if not folder_path.is_dir():
                raise ValueError(
                    f"Google Drive sync path is not a directory: {self.gdrive_sync_folder}. "
                    "Update gdrive_sync_folder or disable sync."
                )

            # Check folder is writable
            try:
                test_file = folder_path / ".gdrive_sync_test"
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError):
                raise ValueError(
                    f"Google Drive folder not writable (permissions issue): {self.gdrive_sync_folder}. "
                    "Check permissions or update path."
                )


def load_config(config_file: str | Path) -> ConfigModel:
    """
    Load and validate configuration from YAML file.

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Validated ConfigModel instance

    Raises:
        FileNotFoundError: Config file not found
        yaml.YAMLError: YAML syntax error
        ValidationError: Config validation failed
    """
    config_file = Path(config_file)

    try:
        # Read YAML file
        with open(config_file, "r") as f:
            config_dict = yaml.safe_load(f)

        if not config_dict:
            raise ValueError("Config file is empty")

        # Validate with Pydantic
        config = ConfigModel(**config_dict)

        # Validate Google Drive config if enabled
        try:
            config.validate_gdrive_config()
        except ValueError as e:
            logger.error(f"Google Drive config validation failed: {str(e)}")
            raise

        logger.info(
            f"✓ Config validated ({config.metadata.course_name}, week {config.metadata.week_number})"
        )
        return config

    except FileNotFoundError:
        error_msg = f"Config file not found: {config_file}"
        logger.error(error_msg)
        raise

    except yaml.YAMLError as e:
        error_msg = f"Config file syntax error: {str(e)}"
        logger.error(error_msg)
        raise

    except ValidationError as e:
        error_msg = "Config validation failed:\n"
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_msg += f"  - {field}: {message}\n"
        logger.error(error_msg)
        raise

    except Exception as e:
        error_msg = f"Error loading config: {str(e)}"
        logger.error(error_msg)
        raise
