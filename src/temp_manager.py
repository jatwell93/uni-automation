"""Temporary file management for tracking and cleanup of pipeline artifacts."""

import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TempFileManager:
    """Singleton manager for tracking and cleaning up temporary files."""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize temp file registry."""
        if not TempFileManager._initialized:
            self._temp_files: Dict[str, Dict] = {}
            self._temp_dirs: Dict[str, Dict] = {}
            TempFileManager._initialized = True

    @classmethod
    def instance(cls):
        """Get singleton instance."""
        return cls()

    def register_temp_file(
        self, file_path: str, stage: str, description: str = ""
    ) -> None:
        """
        Register a temporary file for cleanup.

        Args:
            file_path: Path to temporary file
            stage: Pipeline stage (download, audio, slides, etc.)
            description: Human-readable description of file
        """
        file_path = str(file_path)
        self._temp_files[file_path] = {
            "stage": stage,
            "description": description,
            "created_at": datetime.now().isoformat(),
        }
        logger.debug(f"[temp] Registered temp file: {file_path} ({stage})")

    def register_temp_directory(
        self, dir_path: str, stage: str, description: str = ""
    ) -> None:
        """
        Register a temporary directory for cleanup.

        Args:
            dir_path: Path to temporary directory
            stage: Pipeline stage (download, audio, slides, etc.)
            description: Human-readable description of directory
        """
        dir_path = str(dir_path)
        self._temp_dirs[dir_path] = {
            "stage": stage,
            "description": description,
            "created_at": datetime.now().isoformat(),
        }
        logger.debug(f"[temp] Registered temp directory: {dir_path} ({stage})")

    def cleanup_all(self) -> Dict[str, int]:
        """
        Remove all registered temporary files and directories.

        Returns:
            Dictionary with deleted_count and failed_count
        """
        deleted_count = 0
        failed_count = 0
        failed_paths = []

        # Clean up files
        for file_path in list(self._temp_files.keys()):
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    logger.debug(f"[cleanup] Deleted file: {file_path}")
                    deleted_count += 1
                else:
                    logger.debug(f"[cleanup] File already deleted: {file_path}")
            except PermissionError:
                logger.warning(f"[cleanup] Permission denied: {file_path}")
                failed_count += 1
                failed_paths.append(file_path)
            except Exception as e:
                logger.warning(f"[cleanup] Error deleting {file_path}: {e}")
                failed_count += 1
                failed_paths.append(file_path)

        # Clean up directories
        for dir_path in list(self._temp_dirs.keys()):
            try:
                path = Path(dir_path)
                if path.exists():
                    # Remove directory recursively
                    import shutil

                    shutil.rmtree(path)
                    logger.debug(f"[cleanup] Deleted directory: {dir_path}")
                    deleted_count += 1
                else:
                    logger.debug(f"[cleanup] Directory already deleted: {dir_path}")
            except PermissionError:
                logger.warning(f"[cleanup] Permission denied: {dir_path}")
                failed_count += 1
                failed_paths.append(dir_path)
            except Exception as e:
                logger.warning(f"[cleanup] Error deleting {dir_path}: {e}")
                failed_count += 1
                failed_paths.append(dir_path)

        logger.info(
            f"✓ Cleanup complete: {deleted_count} files/directories removed, "
            f"{failed_count} failed"
        )
        if failed_paths:
            logger.warning(
                f"[cleanup] Failed to delete {failed_count} paths: {failed_paths}"
            )

        return {
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_paths": failed_paths,
        }

    def cleanup_by_stage(self, stage_name: str) -> Dict[str, int]:
        """
        Remove temporary files/directories from specific pipeline stage.

        Args:
            stage_name: Stage name (download, audio, slides, etc.)

        Returns:
            Dictionary with deleted_count and failed_count
        """
        deleted_count = 0
        failed_count = 0
        failed_paths = []

        # Clean up files from this stage
        for file_path in list(self._temp_files.keys()):
            if self._temp_files[file_path]["stage"] == stage_name:
                try:
                    path = Path(file_path)
                    if path.exists():
                        path.unlink()
                        logger.debug(f"[cleanup] Deleted file: {file_path}")
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"[cleanup] Error deleting {file_path}: {e}")
                    failed_count += 1
                    failed_paths.append(file_path)

        # Clean up directories from this stage
        for dir_path in list(self._temp_dirs.keys()):
            if self._temp_dirs[dir_path]["stage"] == stage_name:
                try:
                    path = Path(dir_path)
                    if path.exists():
                        import shutil

                        shutil.rmtree(path)
                        logger.debug(f"[cleanup] Deleted directory: {dir_path}")
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"[cleanup] Error deleting {dir_path}: {e}")
                    failed_count += 1
                    failed_paths.append(dir_path)

        logger.info(
            f"✓ Cleanup stage '{stage_name}': {deleted_count} items removed, "
            f"{failed_count} failed"
        )

        return {
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_paths": failed_paths,
        }

    def get_temp_files(self) -> List[str]:
        """
        Get list of all registered temporary files and directories.

        Returns:
            List of file/directory paths
        """
        return list(self._temp_files.keys()) + list(self._temp_dirs.keys())

    def clear_registry(self) -> None:
        """Clear all registered files (for testing)."""
        self._temp_files.clear()
        self._temp_dirs.clear()
        logger.debug("[temp] Registry cleared")


# Module-level convenience functions
def register_temp_file(file_path: str, stage: str, description: str = "") -> None:
    """Register a temporary file using the singleton instance."""
    TempFileManager.instance().register_temp_file(file_path, stage, description)


def cleanup_temp_files() -> Dict[str, int]:
    """Cleanup all temporary files using the singleton instance."""
    return TempFileManager.instance().cleanup_all()
