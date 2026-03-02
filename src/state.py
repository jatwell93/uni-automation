"""
Pipeline state management for tracking execution flow and recovery.

Manages pipeline execution state, stage skipping for resumed runs,
and cleanup of partial files from failed stages.
"""

import logging
from pathlib import Path
from typing import Optional, List

from src.checkpoint import CheckpointManager, PipelineCheckpoint
from src.config import ConfigModel

logger = logging.getLogger(__name__)


class PipelineState:
    """Manages pipeline execution state and recovery logic."""

    def __init__(
        self,
        config: ConfigModel,
        checkpoint_file: Optional[str] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        """Initialize pipeline state.

        Args:
            config: Validated ConfigModel instance
            checkpoint_file: Path to checkpoint file for resuming failed run
            checkpoint_manager: CheckpointManager instance (created if None)

        Raises:
            FileNotFoundError: If checkpoint_file provided but not found
            ValueError: If checkpoint file is corrupted
        """
        self.config = config
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.checkpoint: Optional[PipelineCheckpoint] = None
        self.skip_stages: List[str] = []
        self.next_stage: Optional[str] = "download"

        # Load checkpoint if provided
        if checkpoint_file:
            self._load_checkpoint(checkpoint_file)
        else:
            # Fresh start
            self.skip_stages = []
            self.next_stage = "download"

    def _load_checkpoint(self, checkpoint_file: str) -> None:
        """Load checkpoint from file.

        Args:
            checkpoint_file: Path to checkpoint file

        Raises:
            FileNotFoundError: If file not found
            ValueError: If checkpoint corrupted
        """
        checkpoint_path = Path(checkpoint_file)

        if not checkpoint_path.exists():
            error_msg = f"Checkpoint file not found: {checkpoint_file}. Run without --retry to start fresh."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            self.checkpoint = self.checkpoint_manager.load(checkpoint_file)

            if self.checkpoint is None:
                raise ValueError(
                    f"Checkpoint corrupted. Delete .state/{checkpoint_path.name} and retry."
                )

            # Validate checkpoint structure
            checkpoint_dict = {
                "lecture_id": self.checkpoint.lecture_id,
                "timestamp": self.checkpoint.timestamp,
                "stages": {
                    name: {
                        "completed": meta.completed,
                        "duration_seconds": meta.duration_seconds,
                        "file_size_bytes": meta.file_size_bytes,
                    }
                    for name, meta in self.checkpoint.stages.items()
                },
                "last_completed_stage": self.checkpoint.last_completed_stage,
                "next_stage": self.checkpoint.next_stage,
            }
            self.checkpoint_manager.validate(checkpoint_dict)

            # Populate skip_stages from checkpoint
            self.skip_stages = [
                stage
                for stage, meta in self.checkpoint.stages.items()
                if meta.completed
            ]
            self.next_stage = self.checkpoint.next_stage or "download"

            logger.info(
                f"Resuming from checkpoint: skipping {len(self.skip_stages)} completed stages "
                f"({', '.join(self.skip_stages)})"
            )
        except ValueError as e:
            if "Checkpoint corrupted" in str(e):
                raise
            error_msg = (
                f"Checkpoint corrupted. Delete .state/{checkpoint_path.name} and retry."
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to load checkpoint: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def get_skip_stages(self) -> List[str]:
        """Get list of stages to skip (already completed).

        Returns:
            List of stage names to skip
        """
        return self.skip_stages.copy()

    def get_next_stage(self) -> Optional[str]:
        """Get the next incomplete stage to execute.

        Returns:
            Stage name or None if all stages complete
        """
        return self.next_stage

    def should_run_stage(self, stage_name: str) -> bool:
        """Check if stage should be run (not in skip list).

        Args:
            stage_name: Name of stage to check

        Returns:
            True if stage should be run, False if should be skipped
        """
        return stage_name not in self.skip_stages

    def mark_stage_complete(self, stage_name: str) -> None:
        """Mark stage as complete.

        Args:
            stage_name: Name of stage to mark complete
        """
        if stage_name not in self.skip_stages:
            self.skip_stages.append(stage_name)

        # Update next_stage
        valid_stages = ["download", "transcript", "audio", "slides", "llm", "output"]
        try:
            current_idx = valid_stages.index(stage_name)
            if current_idx < len(valid_stages) - 1:
                self.next_stage = valid_stages[current_idx + 1]
            else:
                self.next_stage = None
        except ValueError:
            logger.warning(f"Unknown stage: {stage_name}")

    def cleanup_partial_files(self, stage_name: str) -> None:
        """Remove partial/failed output files from a stage.

        Only removes files from the stage being retried, not from skipped stages.

        Args:
            stage_name: Name of stage with partial files to clean up
        """
        if stage_name not in self.skip_stages:
            # Only clean up if the stage is being retried, not if it was skipped
            logger.info(
                f"Cleaning up partial files from failed {stage_name} stage before retry"
            )

            output_dir = Path(self.config.paths.output_dir)
            lecture_id = self._get_lecture_id()

            # Define files to delete per stage
            cleanup_patterns = {
                "download": [f"{lecture_id}.mp4", f"{lecture_id}_video.mp4"],
                "transcript": [
                    f"{lecture_id}_transcript.*",
                    f"{lecture_id}_transcript.vtt",
                ],
                "audio": [f"{lecture_id}_audio.*", f"{lecture_id}_audio.wav"],
                "slides": [
                    f"{lecture_id}_slides_text.*",
                    f"{lecture_id}_slides_text.txt",
                ],
                "llm": [f"{lecture_id}_notes.*", f"{lecture_id}_notes.md"],
                "output": [],  # Output files handled by obsidian_writer
            }

            patterns = cleanup_patterns.get(stage_name, [])

            for pattern in patterns:
                # Handle wildcard patterns
                if "*" in pattern:
                    # Use glob for wildcard matching
                    for file_path in output_dir.glob(pattern):
                        try:
                            file_path.unlink()
                            logger.debug(f"Deleted partial file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete {file_path}: {e}")
                else:
                    # Direct file
                    file_path = output_dir / pattern
                    if file_path.exists():
                        try:
                            file_path.unlink()
                            logger.debug(f"Deleted partial file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete {file_path}: {e}")
        else:
            # Stage was skipped, don't delete its files
            logger.debug(
                f"Skipping cleanup for {stage_name} (stage was already completed)"
            )

    def _get_lecture_id(self) -> str:
        """Extract lecture ID from config.

        Returns:
            Lecture identifier (e.g., 'week_05')
        """
        # Use week number if available
        if hasattr(self.config.metadata, "week_number"):
            return f"week_{self.config.metadata.week_number:02d}"

        # Fallback to generic ID
        return "lecture"

    def get_checkpoint_path(self) -> Optional[str]:
        """Get path to current checkpoint file.

        Returns:
            Path to checkpoint file or None if no checkpoint loaded
        """
        if self.checkpoint:
            return str(
                self.checkpoint_manager.find_latest_checkpoint(
                    self.checkpoint.lecture_id
                )
            )
        return None

    def has_checkpoint(self) -> bool:
        """Check if pipeline is resuming from checkpoint.

        Returns:
            True if resuming from checkpoint, False if fresh start
        """
        return self.checkpoint is not None

    def get_checkpoint_summary(self) -> str:
        """Get human-readable summary of checkpoint state.

        Returns:
            Summary string
        """
        if not self.checkpoint:
            return "Starting fresh (no checkpoint)"

        completed = ", ".join(self.skip_stages)
        return f"Resuming: completed {completed}, next stage: {self.next_stage}"
