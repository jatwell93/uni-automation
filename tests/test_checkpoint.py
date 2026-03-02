"""Tests for checkpoint management system."""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.checkpoint import (
    CheckpointManager,
    PipelineCheckpoint,
    StageStatus,
    StageMetadata,
)


@pytest.fixture
def temp_checkpoint_dir():
    """Create temporary checkpoint directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def checkpoint_manager(temp_checkpoint_dir):
    """Create CheckpointManager instance with temp directory."""
    return CheckpointManager(checkpoint_dir=temp_checkpoint_dir)


class TestCheckpointSaveAndLoad:
    """Tests for checkpoint save/load operations."""

    def test_save_checkpoint_creates_file_with_valid_json(self, checkpoint_manager):
        """Verify save creates JSON file with valid structure."""
        checkpoint_file = checkpoint_manager.save(
            stage_name="download",
            lecture_id="week_05",
            metadata={"duration_seconds": 120, "file_size_bytes": 150000000},
        )

        assert checkpoint_file.exists()
        assert checkpoint_file.suffix == ".json"

        # Verify JSON is valid
        with open(checkpoint_file) as f:
            data = json.load(f)

        assert data["lecture_id"] == "week_05"
        assert data["last_completed_stage"] == "download"
        assert "download" in data["stages"]
        assert data["stages"]["download"]["completed"] is True

    def test_load_checkpoint_reads_json(self, checkpoint_manager, temp_checkpoint_dir):
        """Verify load correctly reads checkpoint file."""
        # Create checkpoint
        checkpoint_file = checkpoint_manager.save(
            stage_name="download",
            lecture_id="week_05",
        )

        # Load it back
        loaded = checkpoint_manager.load(str(checkpoint_file))

        assert loaded is not None
        assert loaded.lecture_id == "week_05"
        assert loaded.last_completed_stage == "download"

    def test_load_nonexistent_file_returns_none(self, checkpoint_manager):
        """Verify load returns None for missing files."""
        result = checkpoint_manager.load("/nonexistent/path/checkpoint.json")
        assert result is None

    def test_checkpoint_roundtrip_save_and_load(self, checkpoint_manager):
        """Verify checkpoint survives save→load roundtrip."""
        # Save
        checkpoint_file = checkpoint_manager.save(
            stage_name="audio",
            lecture_id="week_05",
            metadata={"duration_seconds": 45, "file_size_bytes": 5000000},
        )

        # Load
        loaded = checkpoint_manager.load(str(checkpoint_file))

        # Verify
        assert loaded.lecture_id == "week_05"
        assert loaded.last_completed_stage == "audio"
        assert loaded.stages["audio"].duration_seconds == 45
        assert loaded.stages["audio"].file_size_bytes == 5000000


class TestCheckpointValidation:
    """Tests for checkpoint validation."""

    def test_validate_valid_checkpoint_passes(self):
        """Verify valid checkpoint passes validation."""
        checkpoint_data = {
            "lecture_id": "week_05",
            "timestamp": "2026-03-02T09:00:00Z",
            "stages": {
                "download": {
                    "completed": True,
                    "duration_seconds": 120,
                    "file_size_bytes": 150000000,
                },
            },
            "last_completed_stage": "download",
            "next_stage": "transcript",
        }

        manager = CheckpointManager()
        assert manager.validate(checkpoint_data) is True

    def test_validate_missing_required_fields_raises(self):
        """Verify validation fails with missing fields."""
        checkpoint_data = {
            "lecture_id": "week_05",
            # Missing: timestamp, stages, last_completed_stage, next_stage
        }

        manager = CheckpointManager()
        with pytest.raises(ValueError, match="Missing required fields"):
            manager.validate(checkpoint_data)

    def test_validate_invalid_stage_order_raises(self):
        """Verify validation fails with invalid stage order."""
        # Stages out of order: audio before download
        checkpoint_data = {
            "lecture_id": "week_05",
            "timestamp": "2026-03-02T09:00:00Z",
            "stages": {
                "audio": {"completed": True},
            },
            "last_completed_stage": "audio",
            "next_stage": None,
        }

        manager = CheckpointManager()
        with pytest.raises(ValueError, match="Invalid stage order"):
            manager.validate(checkpoint_data)


class TestStageCompletion:
    """Tests for stage completion tracking."""

    def test_get_last_completed_stage_returns_correct_stage(self):
        """Verify last_completed_stage is correctly identified."""
        checkpoint_data = {
            "lecture_id": "week_05",
            "timestamp": "2026-03-02T09:00:00Z",
            "stages": {
                "download": {"completed": True},
                "audio": {"completed": True},
            },
            "last_completed_stage": "audio",
            "next_stage": "slides",
        }

        manager = CheckpointManager()
        assert manager.get_last_completed_stage(checkpoint_data) == "audio"

    def test_should_skip_stage_when_completed(self):
        """Verify should_skip_stage returns True for completed stages."""
        checkpoint_data = {
            "lecture_id": "week_05",
            "timestamp": "2026-03-02T09:00:00Z",
            "stages": {
                "download": {"completed": True},
            },
            "last_completed_stage": "download",
            "next_stage": "transcript",
        }

        manager = CheckpointManager()
        assert manager.should_skip_stage(checkpoint_data, "download") is True

    def test_should_skip_stage_when_pending(self):
        """Verify should_skip_stage returns False for pending stages."""
        checkpoint_data = {
            "lecture_id": "week_05",
            "timestamp": "2026-03-02T09:00:00Z",
            "stages": {
                "download": {"completed": True},
            },
            "last_completed_stage": "download",
            "next_stage": "transcript",
        }

        manager = CheckpointManager()
        assert manager.should_skip_stage(checkpoint_data, "transcript") is False


class TestCheckpointTimestamp:
    """Tests for timestamp handling."""

    def test_checkpoint_timestamp_format_valid(self, checkpoint_manager):
        """Verify checkpoint timestamp is ISO 8601 format."""
        checkpoint_file = checkpoint_manager.save(
            stage_name="download",
            lecture_id="week_05",
        )

        loaded = checkpoint_manager.load(str(checkpoint_file))

        # Verify ISO 8601 format
        try:
            datetime.fromisoformat(loaded.timestamp)
            assert True
        except ValueError:
            pytest.fail(f"Timestamp not ISO 8601 format: {loaded.timestamp}")


class TestStageStatusEnum:
    """Tests for StageStatus enum."""

    def test_stage_status_enum_values(self):
        """Verify StageStatus enum has correct values."""
        assert StageStatus.PENDING.value == "pending"
        assert StageStatus.IN_PROGRESS.value == "in_progress"
        assert StageStatus.COMPLETED.value == "completed"
        assert StageStatus.FAILED.value == "failed"


class TestMultipleStages:
    """Tests for multi-stage checkpoint progression."""

    def test_save_multiple_stages_updates_checkpoint(self, checkpoint_manager):
        """Verify saving multiple stages updates checkpoint correctly."""
        # Save first stage
        checkpoint_file_1 = checkpoint_manager.save(
            stage_name="download",
            lecture_id="week_05",
            metadata={"duration_seconds": 120, "file_size_bytes": 150000000},
        )

        checkpoint_1 = checkpoint_manager.load(str(checkpoint_file_1))

        # Save second stage
        checkpoint_file_2 = checkpoint_manager.save(
            stage_name="audio",
            lecture_id="week_05",
            metadata={"duration_seconds": 45, "file_size_bytes": 5000000},
            checkpoint=checkpoint_1,
        )

        checkpoint_2 = checkpoint_manager.load(str(checkpoint_file_2))

        # Verify both stages are in checkpoint
        assert "download" in checkpoint_2.stages
        assert "audio" in checkpoint_2.stages
        assert checkpoint_2.last_completed_stage == "audio"
        assert checkpoint_2.next_stage == "slides"


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_stage_name_raises(self, checkpoint_manager):
        """Verify invalid stage name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid stage"):
            checkpoint_manager.save(
                stage_name="invalid_stage",
                lecture_id="week_05",
            )

    def test_malformed_json_raises(self, checkpoint_manager, temp_checkpoint_dir):
        """Verify malformed JSON raises JSONDecodeError."""
        # Create malformed JSON file
        bad_file = Path(temp_checkpoint_dir) / "bad_checkpoint.json"
        bad_file.write_text("{invalid json content")

        with pytest.raises(ValueError, match="Invalid checkpoint file"):
            checkpoint_manager.load(str(bad_file))


class TestFindLatestCheckpoint:
    """Tests for finding latest checkpoint."""

    def test_find_latest_checkpoint_returns_newest_file(self, checkpoint_manager):
        """Verify find_latest_checkpoint returns most recent file."""
        # Save first checkpoint
        file_1 = checkpoint_manager.save(
            stage_name="download",
            lecture_id="week_05",
        )

        # Load and update for second stage
        checkpoint_1 = checkpoint_manager.load(str(file_1))
        file_2 = checkpoint_manager.save(
            stage_name="audio",
            lecture_id="week_05",
            checkpoint=checkpoint_1,
        )

        # Find latest
        latest = checkpoint_manager.find_latest_checkpoint("week_05")

        # Should be the second one (saved later)
        assert latest is not None
        # The filenames contain timestamps, second should be newer
        loaded = checkpoint_manager.load(str(latest))
        assert "audio" in loaded.stages
        assert loaded.last_completed_stage == "audio"

    def test_find_latest_checkpoint_returns_none_if_not_found(self, checkpoint_manager):
        """Verify find_latest_checkpoint returns None if no file found."""
        result = checkpoint_manager.find_latest_checkpoint("nonexistent_week")
        assert result is None
