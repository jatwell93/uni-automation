"""
Checkpoint management for pipeline state persistence and recovery.

Enables failed runs to resume from the last completed stage without
re-downloading or re-processing completed work.
"""

import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StageStatus(Enum):
    """Pipeline stage execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StageMetadata:
    """Metadata about a completed stage."""

    completed: bool
    duration_seconds: float = 0
    file_size_bytes: int = 0


@dataclass
class PipelineCheckpoint:
    """Checkpoint data structure for pipeline state."""

    lecture_id: str
    timestamp: str  # ISO 8601 format
    stages: Dict[str, StageMetadata]
    last_completed_stage: Optional[str]
    next_stage: Optional[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "lecture_id": self.lecture_id,
            "timestamp": self.timestamp,
            "stages": {
                name: {
                    "completed": meta.completed,
                    "duration_seconds": meta.duration_seconds,
                    "file_size_bytes": meta.file_size_bytes,
                }
                for name, meta in self.stages.items()
            },
            "last_completed_stage": self.last_completed_stage,
            "next_stage": self.next_stage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineCheckpoint":
        """Create checkpoint from dictionary."""
        stages = {}
        for name, meta in data.get("stages", {}).items():
            stages[name] = StageMetadata(
                completed=meta.get("completed", False),
                duration_seconds=meta.get("duration_seconds", 0),
                file_size_bytes=meta.get("file_size_bytes", 0),
            )
        return cls(
            lecture_id=data["lecture_id"],
            timestamp=data["timestamp"],
            stages=stages,
            last_completed_stage=data.get("last_completed_stage"),
            next_stage=data.get("next_stage"),
        )


class CheckpointManager:
    """Manages checkpoint persistence and recovery for pipeline stages."""

    # Valid stage order
    VALID_STAGES = ["download", "transcript", "audio", "slides", "llm", "output"]

    def __init__(self, checkpoint_dir: str = ".state"):
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        stage_name: str,
        lecture_id: str,
        metadata: Optional[Dict[str, any]] = None,
        checkpoint: Optional[PipelineCheckpoint] = None,
    ) -> Path:
        """Save checkpoint after stage completion.

        Args:
            stage_name: Name of the completed stage
            lecture_id: Unique lecture identifier
            metadata: Optional metadata (duration_seconds, file_size_bytes)
            checkpoint: Optional existing checkpoint to update

        Returns:
            Path to checkpoint file

        Raises:
            ValueError: If stage_name invalid
        """
        if stage_name not in self.VALID_STAGES:
            raise ValueError(
                f"Invalid stage: {stage_name}. Valid stages: {self.VALID_STAGES}"
            )

        if metadata is None:
            metadata = {}

        # Create or update checkpoint
        if checkpoint is None:
            checkpoint = PipelineCheckpoint(
                lecture_id=lecture_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stages={},
                last_completed_stage=None,
                next_stage=None,
            )

        # Update stage
        checkpoint.stages[stage_name] = StageMetadata(
            completed=True,
            duration_seconds=metadata.get("duration_seconds", 0),
            file_size_bytes=metadata.get("file_size_bytes", 0),
        )
        checkpoint.last_completed_stage = stage_name

        # Calculate next stage
        current_idx = self.VALID_STAGES.index(stage_name)
        if current_idx < len(self.VALID_STAGES) - 1:
            checkpoint.next_stage = self.VALID_STAGES[current_idx + 1]
        else:
            checkpoint.next_stage = None

        # Write checkpoint file
        checkpoint_file = (
            self.checkpoint_dir
            / f"{lecture_id}_{checkpoint.timestamp.replace(':', '-')}.json"
        )

        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

            file_size = checkpoint_file.stat().st_size
            logger.info(
                f"✓ Stage {stage_name} completed, checkpoint saved ({file_size} bytes)"
            )
            return checkpoint_file
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise

    def load(self, checkpoint_file: str) -> Optional[PipelineCheckpoint]:
        """Load checkpoint from file.

        Args:
            checkpoint_file: Path to checkpoint file

        Returns:
            PipelineCheckpoint or None if file not found

        Raises:
            json.JSONDecodeError: If file is malformed
        """
        filepath = Path(checkpoint_file)

        if not filepath.exists():
            logger.debug(f"Checkpoint file not found: {checkpoint_file}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint = PipelineCheckpoint.from_dict(data)
            logger.info(
                f"↻ Resuming from checkpoint: last completed stage = {checkpoint.last_completed_stage}"
            )
            return checkpoint
        except json.JSONDecodeError as e:
            error_msg = f"Invalid checkpoint file: {checkpoint_file}. Delete .state/{filepath.name} and retry"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def validate(self, checkpoint: Dict) -> bool:
        """Validate checkpoint structure and stage order.

        Args:
            checkpoint: Checkpoint dictionary to validate

        Returns:
            True if valid

        Raises:
            ValueError: If checkpoint invalid
        """
        # Check required fields
        required_fields = {
            "lecture_id",
            "timestamp",
            "stages",
            "last_completed_stage",
            "next_stage",
        }
        if not all(field in checkpoint for field in required_fields):
            missing = required_fields - set(checkpoint.keys())
            raise ValueError(f"Missing required fields in checkpoint: {missing}")

        # Validate stage order
        completed_stages = [
            stage
            for stage, meta in checkpoint.get("stages", {}).items()
            if meta.get("completed", False)
        ]

        # Check that all completed stages follow valid order
        for stage in completed_stages:
            if stage not in self.VALID_STAGES:
                raise ValueError(f"Invalid stage in checkpoint: {stage}")

        # Check that stages are in order (no gaps)
        valid_order = self.VALID_STAGES[: len(completed_stages)]
        for i, stage in enumerate(completed_stages):
            if stage != valid_order[i]:
                raise ValueError(
                    f"Invalid stage order in checkpoint. Expected {valid_order}, got {completed_stages}"
                )

        return True

    def get_last_completed_stage(self, checkpoint: Dict) -> Optional[str]:
        """Get the last completed stage from checkpoint.

        Args:
            checkpoint: Checkpoint dictionary

        Returns:
            Stage name or None if no stages completed
        """
        return checkpoint.get("last_completed_stage")

    def should_skip_stage(self, checkpoint: Dict, stage_name: str) -> bool:
        """Check if stage should be skipped (already completed).

        Args:
            checkpoint: Checkpoint dictionary
            stage_name: Stage to check

        Returns:
            True if stage already completed and should be skipped
        """
        if checkpoint is None:
            return False

        stages = checkpoint.get("stages", {})
        stage_meta = stages.get(stage_name, {})
        return stage_meta.get("completed", False)

    def find_latest_checkpoint(self, lecture_id: str) -> Optional[Path]:
        """Find the most recent checkpoint file for a lecture.

        Args:
            lecture_id: Lecture identifier

        Returns:
            Path to latest checkpoint file or None if not found
        """
        # Find all checkpoint files for this lecture_id
        pattern = f"{lecture_id}_*.json"
        matching_files = list(self.checkpoint_dir.glob(pattern))

        if not matching_files:
            return None

        # Sort by modification time, return latest
        return max(matching_files, key=lambda p: p.stat().st_mtime)
