"""Tests for configuration module."""

import pytest
from pathlib import Path
import tempfile
import yaml
from pydantic import ValidationError

from src.config import ConfigModel, load_config


class TestPydanticModel:
    """Test Pydantic configuration model validation."""

    def test_valid_config(self):
        """Test loading a valid configuration."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create required slide file
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()

            # Update config with absolute path
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            assert config.lecture.url == "https://example.com/panopto"
            assert config.metadata.course_name == "Unknown Course"
            assert config.metadata.week_number == 1

    def test_optional_metadata(self):
        """Test that metadata fields have sensible defaults."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "metadata": {
                "course_name": "Advanced Topics",
                "week_number": 3,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()

            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            assert config.metadata.course_name == "Advanced Topics"
            assert config.metadata.week_number == 3
            assert config.metadata.lecturer_name == ""

    def test_invalid_url(self):
        """Test URL validation rejects invalid URLs."""
        config_dict = {
            "lecture": {
                "url": "not-a-valid-url",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            ConfigModel(**config_dict)
        assert "Invalid URL" in str(exc_info.value)

    def test_missing_slide_path(self):
        """Test validation fails when slide path doesn't exist."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "nonexistent/slides.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            ConfigModel(**config_dict)
        assert "does not exist" in str(exc_info.value)

    def test_missing_paths_section(self):
        """Test validation fails when paths section is missing."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            ConfigModel(**config_dict)
        assert "paths" in str(exc_info.value).lower()

    def test_output_dir_writable(self):
        """Test output directory writability check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()

            output_dir = Path(tmpdir) / "outputs"

            config_dict = {
                "lecture": {
                    "url": "https://example.com/panopto",
                    "slide_path": str(slide_path),
                },
                "paths": {
                    "cookie_file": "cookies/test.json",
                    "output_dir": str(output_dir),
                },
            }

            config = ConfigModel(**config_dict)
            # Verify directory was created
            assert output_dir.exists()


class TestLoadConfig:
    """Test load_config() function."""

    def test_load_valid_yaml(self):
        """Test loading a valid YAML config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create slide file
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()

            # Create config file
            config_path = Path(tmpdir) / "config.yaml"
            output_dir = Path(tmpdir) / "downloads"
            # Use forward slashes for YAML
            slide_path_str = str(slide_path).replace("\\", "/")
            output_dir_str = str(output_dir).replace("\\", "/")
            config_content = f"""
lecture:
  url: "https://example.com/panopto"
  slide_path: "{slide_path_str}"
paths:
  cookie_file: "cookies/test.json"
  output_dir: "{output_dir_str}"
metadata:
  course_name: "Test Course"
  week_number: 1
"""
            config_path.write_text(config_content)

            config = load_config(str(config_path))
            assert config.metadata.course_name == "Test Course"
            assert config.lecture.url == "https://example.com/panopto"

    def test_load_nonexistent_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent/config.yaml")

    def test_load_invalid_yaml(self):
        """Test error on invalid YAML syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("invalid: yaml: syntax:\n  bad indentation here:")

            with pytest.raises(Exception):  # yaml.YAMLError or similar
                load_config(str(config_path))

    def test_load_empty_file(self):
        """Test error on empty config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("")

            with pytest.raises(Exception):
                load_config(str(config_path))

    def test_load_with_validation_error(self):
        """Test clear error messages on validation failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            # Use proper YAML format
            config_content = "lecture:\n  url: 'invalid-url'\n"
            config_path.write_text(config_content)

            with pytest.raises(Exception) as exc_info:
                load_config(str(config_path))

            error_msg = str(exc_info.value)
            assert "lecture" in error_msg.lower() or "invalid" in error_msg.lower()

    def test_load_missing_required_field(self):
        """Test error when required fields are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_content = "lecture:\n  url: 'https://example.com'\n"
            config_path.write_text(config_content)

            with pytest.raises(Exception):
                load_config(str(config_path))
