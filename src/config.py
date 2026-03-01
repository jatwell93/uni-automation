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
