"""Tests for pipeline state management."""

import pytest
import tempfile
from pathlib import Path

from src.state import PipelineState
from src.checkpoint import CheckpointManager, PipelineCheckpoint, StageMetadata
from src.config import ConfigModel, LectureConfig, PathsConfig, MetadataConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_output_dir(temp_dir):
    """Create temporary output directory."""
    output_dir = Path(temp_dir) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


@pytest.fixture
def mock_config(temp_output_dir):
    """Create mock ConfigModel for testing."""
    return ConfigModel(
        lecture=LectureConfig(
            url="https://example.com/lecture",
            slide_path="",
        ),
        paths=PathsConfig(
            cookie_file="cookies.json",
            output_dir=temp_output_dir,
        ),
        metadata=MetadataConfig(
            course_name="Test Course",
            week_number=5,
        ),
    )


@pytest.fixture
def checkpoint_manager(temp_dir):
    """Create CheckpointManager with temp checkpoint directory."""
    return CheckpointManager(checkpoint_dir=Path(temp_dir) / ".state")


class TestPipelineStateInitialization:
    """Tests for PipelineState initialization."""

    def test_init_without_checkpoint_starts_at_download(self, mock_config):
        """Verify fresh start initializes with download as first stage."""
        state = PipelineState(config=mock_config)

        assert state.get_next_stage() == "download"
        assert state.get_skip_stages() == []
        assert state.has_checkpoint() is False

    def test_init_from_checkpoint_loads_skip_stages(
        self, mock_config, checkpoint_manager, temp_dir
    ):
        """Verify loading checkpoint sets skip_stages correctly."""
        # Create a checkpoint with download, transcript, and audio completed
        checkpoint = PipelineCheckpoint(
            lecture_id="week_05",
            timestamp="2026-03-02T09:00:00Z",
            stages={
                "download": StageMetadata(completed=True),
                "transcript": StageMetadata(completed=True),
                "audio": StageMetadata(completed=True),
            },
            last_completed_stage="audio",
            next_stage="slides",
        )

        # Save checkpoint
        checkpoint_file = Path(temp_dir) / ".state" / "checkpoint.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        import json

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f)

        # Load state from checkpoint
        state = PipelineState(
            config=mock_config,
            checkpoint_file=str(checkpoint_file),
            checkpoint_manager=checkpoint_manager,
        )

        assert state.has_checkpoint() is True
        assert set(state.get_skip_stages()) == {"download", "transcript", "audio"}
        assert state.get_next_stage() == "slides"


class TestStageSkipping:
    """Tests for stage skipping logic."""

    def test_get_skip_stages_returns_completed(
        self, mock_config, checkpoint_manager, temp_dir
    ):
        """Verify get_skip_stages returns completed stages."""
        checkpoint = PipelineCheckpoint(
            lecture_id="week_05",
            timestamp="2026-03-02T09:00:00Z",
            stages={
                "download": StageMetadata(completed=True),
                "transcript": StageMetadata(completed=True),
            },
            last_completed_stage="transcript",
            next_stage="audio",
        )

        checkpoint_file = Path(temp_dir) / ".state" / "checkpoint.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        import json

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f)

        state = PipelineState(
            config=mock_config,
            checkpoint_file=str(checkpoint_file),
            checkpoint_manager=checkpoint_manager,
        )

        skip_stages = state.get_skip_stages()
        assert "download" in skip_stages
        assert "transcript" in skip_stages
        assert "audio" not in skip_stages

    def test_should_run_stage_returns_true_for_unskipped(self, mock_config):
        """Verify should_run_stage returns True for pending stages."""
        state = PipelineState(config=mock_config)

        # All stages should run in fresh state
        assert state.should_run_stage("download") is True
        assert state.should_run_stage("audio") is True
        assert state.should_run_stage("llm") is True

    def test_should_run_stage_returns_false_for_skipped(
        self, mock_config, checkpoint_manager, temp_dir
    ):
        """Verify should_run_stage returns False for completed stages."""
        checkpoint = PipelineCheckpoint(
            lecture_id="week_05",
            timestamp="2026-03-02T09:00:00Z",
            stages={
                "download": StageMetadata(completed=True),
            },
            last_completed_stage="download",
            next_stage="transcript",
        )

        checkpoint_file = Path(temp_dir) / ".state" / "checkpoint.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        import json

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f)

        state = PipelineState(
            config=mock_config,
            checkpoint_file=str(checkpoint_file),
            checkpoint_manager=checkpoint_manager,
        )

        assert state.should_run_stage("download") is False
        assert state.should_run_stage("transcript") is True


class TestGetNextStage:
    """Tests for getting next stage."""

    def test_get_next_stage_returns_incomplete(self, mock_config):
        """Verify get_next_stage returns next incomplete stage."""
        state = PipelineState(config=mock_config)
        assert state.get_next_stage() == "download"

    def test_get_next_stage_after_mark_complete(self, mock_config):
        """Verify get_next_stage updates after marking stage complete."""
        state = PipelineState(config=mock_config)

        state.mark_stage_complete("download")
        assert state.get_next_stage() == "transcript"

        state.mark_stage_complete("transcript")
        assert state.get_next_stage() == "audio"


class TestMarkStageComplete:
    """Tests for marking stages complete."""

    def test_mark_stage_complete_updates_state(self, mock_config):
        """Verify mark_stage_complete adds stage to skip list."""
        state = PipelineState(config=mock_config)

        assert "download" not in state.get_skip_stages()

        state.mark_stage_complete("download")

        assert "download" in state.get_skip_stages()

    def test_mark_multiple_stages_complete(self, mock_config):
        """Verify marking multiple stages works correctly."""
        state = PipelineState(config=mock_config)

        state.mark_stage_complete("download")
        state.mark_stage_complete("transcript")
        state.mark_stage_complete("audio")

        skip_stages = state.get_skip_stages()
        assert "download" in skip_stages
        assert "transcript" in skip_stages
        assert "audio" in skip_stages


class TestCleanupPartialFiles:
    """Tests for partial file cleanup."""

    def test_cleanup_partial_files_removes_failed_stage_artifacts(
        self, mock_config, checkpoint_manager, temp_dir, temp_output_dir
    ):
        """Verify cleanup removes files when retrying failed stage."""
        # Create checkpoint with download and transcript completed,
        # but audio failed (has partial files)
        checkpoint = PipelineCheckpoint(
            lecture_id="week_05",
            timestamp="2026-03-02T09:00:00Z",
            stages={
                "download": StageMetadata(completed=True),
                "transcript": StageMetadata(completed=True),
            },
            last_completed_stage="transcript",
            next_stage="audio",
        )

        checkpoint_file = Path(temp_dir) / ".state" / "checkpoint.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        import json

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f)

        state = PipelineState(
            config=mock_config,
            checkpoint_file=str(checkpoint_file),
            checkpoint_manager=checkpoint_manager,
        )

        # Create partial audio files from failed attempt
        output_path = Path(temp_output_dir)
        (output_path / "week_05_audio.wav").write_text("partial audio")

        # Cleanup audio stage (not in skip_stages, so it will be deleted)
        state.cleanup_partial_files("audio")

        # File should be deleted since audio is being retried
        assert not (output_path / "week_05_audio.wav").exists()

    def test_cleanup_preserves_skipped_stage_files(
        self, mock_config, checkpoint_manager, temp_dir, temp_output_dir
    ):
        """Verify cleanup doesn't delete files from skipped stages."""
        # Create checkpoint with download completed
        checkpoint = PipelineCheckpoint(
            lecture_id="week_05",
            timestamp="2026-03-02T09:00:00Z",
            stages={
                "download": StageMetadata(completed=True),
            },
            last_completed_stage="download",
            next_stage="transcript",
        )

        checkpoint_file = Path(temp_dir) / ".state" / "checkpoint.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        import json

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f)

        state = PipelineState(
            config=mock_config,
            checkpoint_file=str(checkpoint_file),
            checkpoint_manager=checkpoint_manager,
        )

        # Create partial download file
        output_path = Path(temp_output_dir)
        video_file = output_path / "week_05.mp4"
        video_file.write_text("partial video")

        # Cleanup download - should NOT delete since it's in skip_stages
        state.cleanup_partial_files("download")

        # File should still exist
        assert video_file.exists()


class TestStateWithAllStagesComplete:
    """Tests for state when all stages complete."""

    def test_state_with_all_stages_complete_returns_none_for_next_stage(
        self, mock_config
    ):
        """Verify next_stage is None when all stages complete."""
        state = PipelineState(config=mock_config)

        # Mark all stages complete
        for stage in ["download", "transcript", "audio", "slides", "llm", "output"]:
            state.mark_stage_complete(stage)

        assert state.get_next_stage() is None


class TestErrorHandling:
    """Tests for error handling in state management."""

    def test_init_with_missing_checkpoint_file_raises(self, mock_config):
        """Verify missing checkpoint file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            PipelineState(
                config=mock_config,
                checkpoint_file="/nonexistent/checkpoint.json",
            )

    def test_init_with_corrupted_checkpoint_raises(self, mock_config, temp_dir):
        """Verify corrupted checkpoint raises ValueError."""
        # Create corrupted checkpoint file
        checkpoint_file = Path(temp_dir) / "bad_checkpoint.json"
        checkpoint_file.write_text("invalid json")

        with pytest.raises(ValueError, match="Checkpoint corrupted"):
            PipelineState(
                config=mock_config,
                checkpoint_file=str(checkpoint_file),
            )


class TestCheckpointSummary:
    """Tests for checkpoint summary information."""

    def test_get_checkpoint_summary_fresh_start(self, mock_config):
        """Verify summary for fresh start."""
        state = PipelineState(config=mock_config)
        summary = state.get_checkpoint_summary()
        assert "fresh" in summary.lower()

    def test_get_checkpoint_summary_with_checkpoint(
        self, mock_config, checkpoint_manager, temp_dir
    ):
        """Verify summary includes completed stages."""
        checkpoint = PipelineCheckpoint(
            lecture_id="week_05",
            timestamp="2026-03-02T09:00:00Z",
            stages={
                "download": StageMetadata(completed=True),
                "transcript": StageMetadata(completed=True),
                "audio": StageMetadata(completed=True),
            },
            last_completed_stage="audio",
            next_stage="slides",
        )

        checkpoint_file = Path(temp_dir) / ".state" / "checkpoint.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        import json

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f)

        state = PipelineState(
            config=mock_config,
            checkpoint_file=str(checkpoint_file),
            checkpoint_manager=checkpoint_manager,
        )

        summary = state.get_checkpoint_summary()
        assert "Resuming" in summary
        assert "download" in summary
        assert "audio" in summary
