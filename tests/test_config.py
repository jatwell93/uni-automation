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


class TestObsidianConfig:
    """Tests for Obsidian-related configuration fields."""

    def test_config_obsidian_vault_path_required(self):
        """Missing obsidian_vault_path field (can be empty string, but field exists)."""
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
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            # Should create config with default empty vault path
            config = ConfigModel(**config_dict)
            assert config.obsidian_vault_path == ""

    def test_config_obsidian_vault_path_empty_string_invalid(self):
        """Empty string for vault path is invalid if explicitly set to whitespace."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "obsidian_vault_path": "   ",  # Whitespace only
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            with pytest.raises(ValidationError):
                ConfigModel(**config_dict)

    def test_config_obsidian_vault_path_valid(self):
        """Valid obsidian vault path accepted."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "obsidian_vault_path": "/path/to/vault",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            assert config.obsidian_vault_path == "/path/to/vault"


class TestOpenRouterConfig:
    """Tests for OpenRouter API configuration."""

    def test_config_openrouter_api_key_required(self):
        """OpenRouter API key defaults to empty."""
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
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            assert config.openrouter_api_key == ""

    def test_config_openrouter_api_key_empty_string_invalid(self):
        """Empty/whitespace string for API key is invalid if explicitly set."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "openrouter_api_key": "   ",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            with pytest.raises(ValidationError):
                ConfigModel(**config_dict)


class TestLLMBudgetConfig:
    """Tests for LLM budget configuration."""

    def test_config_llm_budget_aud_valid_range(self):
        """LLM budget in valid range (0.01-1.00) accepted."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "llm_budget_aud": 0.50,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            assert config.llm_budget_aud == 0.50

    def test_config_llm_budget_aud_too_low(self):
        """Budget below 0.01 rejected."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "llm_budget_aud": 0.001,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            with pytest.raises(ValidationError):
                ConfigModel(**config_dict)

    def test_config_llm_budget_aud_too_high(self):
        """Budget above 1.00 rejected."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "llm_budget_aud": 1.50,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            with pytest.raises(ValidationError):
                ConfigModel(**config_dict)


class TestLLMSafetyBufferConfig:
    """Tests for LLM safety buffer configuration."""

    def test_config_safety_buffer_valid_range(self):
        """Safety buffer in valid range (0.0-0.5) accepted."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "llm_safety_buffer": 0.25,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            assert config.llm_safety_buffer == 0.25

    def test_config_safety_buffer_too_high(self):
        """Safety buffer above 0.5 rejected."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "llm_safety_buffer": 0.6,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            with pytest.raises(ValidationError):
                ConfigModel(**config_dict)


class TestGoogleDriveConfig:
    """Tests for Google Drive sync configuration."""

    def test_gdrive_sync_folder_optional_when_disabled(self):
        """Google Drive folder optional when gdrive_sync_enabled=False."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "gdrive_sync_enabled": False,
            "gdrive_sync_folder": None,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            # Should not raise
            config = ConfigModel(**config_dict)
            config.validate_gdrive_config()
            assert config.gdrive_sync_enabled is False

    def test_gdrive_sync_enabled_requires_folder_path(self):
        """Google Drive folder required when gdrive_sync_enabled=True."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "gdrive_sync_enabled": True,
            "gdrive_sync_folder": None,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            with pytest.raises(ValueError, match="folder path not set"):
                config.validate_gdrive_config()

    def test_gdrive_sync_folder_validated_exists(self):
        """Google Drive folder must exist when enabled."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "gdrive_sync_enabled": True,
            "gdrive_sync_folder": "/nonexistent/gdrive/path",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            config = ConfigModel(**config_dict)
            with pytest.raises(ValueError, match="not found"):
                config.validate_gdrive_config()

    def test_gdrive_sync_folder_validated_writable(self):
        """Google Drive folder must be writable when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a readable directory
            gdrive_dir = Path(tmpdir) / "gdrive"
            gdrive_dir.mkdir()

            config_dict = {
                "lecture": {
                    "url": "https://example.com/panopto",
                    "slide_path": "slides/test.pdf",
                },
                "paths": {
                    "cookie_file": "cookies/test.json",
                    "output_dir": str(Path(tmpdir) / "downloads"),
                },
                "gdrive_sync_enabled": True,
                "gdrive_sync_folder": str(gdrive_dir),
            }

            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)

            config = ConfigModel(**config_dict)
            # Should not raise when folder is writable
            config.validate_gdrive_config()

    def test_gdrive_config_example_in_yaml_valid(self):
        """Example config with gdrive settings is valid."""
        config_dict = {
            "lecture": {
                "url": "https://example.com/panopto",
                "slide_path": "slides/test.pdf",
            },
            "paths": {
                "cookie_file": "cookies/test.json",
                "output_dir": "downloads/test",
            },
            "gdrive_sync_enabled": False,
            "gdrive_sync_folder": "",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slides" / "test.pdf"
            slide_path.parent.mkdir(parents=True, exist_ok=True)
            slide_path.touch()
            config_dict["lecture"]["slide_path"] = str(slide_path)
            config_dict["paths"]["output_dir"] = str(Path(tmpdir) / "downloads")

            # Should not raise
            config = ConfigModel(**config_dict)
            config.validate_gdrive_config()
            assert config.gdrive_sync_enabled is False
            assert config.gdrive_sync_folder == ""


class TestExampleConfigValid:
    """Tests for the example configuration file."""

    def test_config_example_file_valid_structure(self):
        """Example config file has valid structure."""
        example_path = Path("config/example_week_05.yaml")
        if example_path.exists():
            with open(example_path) as f:
                config_dict = yaml.safe_load(f)

            # Should have basic required fields
            assert "lecture" in config_dict
            assert "paths" in config_dict
            assert "obsidian_vault_path" in config_dict
            assert "openrouter_api_key" in config_dict
