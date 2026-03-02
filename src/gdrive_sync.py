"""Google Drive local sync manager for copying and validating processed artifacts."""

import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SyncError:
    """Details about a failed file sync operation."""

    file: str  # Filename (e.g., "transcript.txt")
    error: str  # Error message
    recovery_action: str  # User-facing recovery instruction


@dataclass
class SyncResult:
    """Result of a Google Drive sync operation."""

    success: bool  # True if all files synced successfully
    synced_files: int  # Count of successfully synced files
    failed_files: int  # Count of failed file syncs
    total_size_bytes: int  # Total size of synced files in bytes
    errors: List[SyncError]  # List of errors for failed files
    sync_duration_seconds: float  # Duration of sync operation


def slugify_course_name(course_name: str) -> str:
    """
    Convert course name to slug format (lowercase, spaces→hyphens, special chars removed).

    Args:
        course_name: Original course name (e.g., "Data & Analytics")

    Returns:
        Slugified course name (e.g., "data-analytics")
    """
    # Lowercase and replace spaces and special chars with hyphens
    slug = course_name.lower().strip()
    slug = slug.replace(" ", "-")

    # Remove special characters except hyphens
    slug = "".join(c if c.isalnum() or c == "-" else "" for c in slug)

    # Replace multiple consecutive hyphens with single hyphen
    while "--" in slug:
        slug = slug.replace("--", "-")

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def validate_gdrive_folder(folder_path: str) -> Tuple[bool, str]:
    """
    Validate that a Google Drive sync folder exists and is writable.

    Args:
        folder_path: Path to Google Drive sync folder

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        path = Path(folder_path)

        # Check if folder exists
        if not path.exists():
            return (
                False,
                f"Google Drive sync folder not found: {folder_path}. "
                "Set up Google Drive local sync or update gdrive_sync_folder in config.",
            )

        # Check if it's a directory
        if not path.is_dir():
            return (
                False,
                f"Google Drive sync path is not a directory: {folder_path}. "
                "Update gdrive_sync_folder in config.",
            )

        # Check if writable
        if not (path / ".test_write").parent.resolve() == path.resolve():
            # Indirect check: try to create test file
            test_file = path / ".gdrive_sync_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError):
                return (
                    False,
                    f"Google Drive folder not writable: {folder_path}. "
                    "Check permissions or reconfigure path.",
                )

        return (True, "")

    except Exception as e:
        return (False, f"Google Drive folder path invalid: {folder_path}. Error: {e}")


class GoogleDriveSyncManager:
    """Manages copying processed artifacts to Google Drive local sync folder."""

    def __init__(self, config):
        """
        Initialize GoogleDriveSyncManager with configuration.

        Args:
            config: ConfigModel instance with gdrive_sync_folder and gdrive_sync_enabled

        Raises:
            ValueError: If Google Drive sync is enabled but folder is invalid
        """
        self.config = config
        self.gdrive_sync_folder = (
            Path(config.gdrive_sync_folder) if config.gdrive_sync_folder else None
        )

        # Validate folder exists and is writable
        if self.gdrive_sync_folder:
            valid, error_msg = validate_gdrive_folder(str(self.gdrive_sync_folder))
            if not valid:
                raise ValueError(error_msg)

    def get_course_subfolder_path(self, course_name: str, week_number: int) -> Path:
        """
        Get (and create if needed) course/week subfolder path in Google Drive.

        Args:
            course_name: Course name (e.g., "Business Analytics")
            week_number: Week number (e.g., 5)

        Returns:
            Path to {gdrive_folder}/{course_slug}/Week_{week}/

        Raises:
            ValueError: If folder creation fails
        """
        if not self.gdrive_sync_folder:
            raise ValueError("Google Drive sync folder not configured")

        # Create course slug
        course_slug = slugify_course_name(course_name)

        # Build path
        subfolder_path = (
            self.gdrive_sync_folder / course_slug / f"Week_{week_number:02d}"
        )

        try:
            subfolder_path.mkdir(parents=True, exist_ok=True)
            return subfolder_path
        except (OSError, PermissionError) as e:
            raise ValueError(
                f"Cannot create Google Drive subfolder: {subfolder_path}. "
                f"Check permissions or reconfigure path. Error: {e}"
            )

    def validate_file_copy(
        self, source_path: str, target_path: str
    ) -> Tuple[bool, str]:
        """
        Validate that a file copy was successful.

        Checks:
        - Target file exists
        - Target file size matches source file size

        Args:
            source_path: Path to source file
            target_path: Path to target file

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            source = Path(source_path)
            target = Path(target_path)

            # Check target file exists
            if not target.exists():
                return (False, "Target file not found after copy")

            # Check target file is readable
            if not target.is_file():
                return (False, "Target is not a regular file")

            # Check sizes match
            source_size = source.stat().st_size
            target_size = target.stat().st_size

            if source_size != target_size:
                return (
                    False,
                    f"Target file size {target_size} != source {source_size} bytes. "
                    "File copy may be incomplete or corrupted.",
                )

            return (True, "")

        except Exception as e:
            return (False, f"Validation error: {e}")

    def sync_artifacts(
        self,
        lecture_id: str,
        transcript_path: str,
        audio_path: str,
        slides_text_path: str,
        course_name: str,
        week_number: int,
    ) -> SyncResult:
        """
        Copy processed artifacts (transcript, audio, slides) to Google Drive.

        Args:
            lecture_id: Identifier for this lecture (e.g., "week_05")
            transcript_path: Path to processed transcript file
            audio_path: Path to extracted audio file
            slides_text_path: Path to extracted slide text file
            course_name: Course name (e.g., "Business Analytics")
            week_number: Week number (e.g., 5)

        Returns:
            SyncResult with success status, file counts, and error details
        """
        start_time = time.time()
        synced_files = 0
        failed_files = 0
        total_size_bytes = 0
        errors: List[SyncError] = []

        try:
            if not self.gdrive_sync_folder:
                return SyncResult(
                    success=False,
                    synced_files=0,
                    failed_files=3,
                    total_size_bytes=0,
                    errors=[
                        SyncError(
                            file="all",
                            error="Google Drive sync folder not configured",
                            recovery_action="Set gdrive_sync_folder in config and enable gdrive_sync_enabled",
                        )
                    ],
                    sync_duration_seconds=time.time() - start_time,
                )

            # Get target folder
            try:
                target_folder = self.get_course_subfolder_path(course_name, week_number)
            except ValueError as e:
                return SyncResult(
                    success=False,
                    synced_files=0,
                    failed_files=3,
                    total_size_bytes=0,
                    errors=[
                        SyncError(
                            file="all",
                            error=str(e),
                            recovery_action="Check Google Drive folder permissions or reconfigure path",
                        )
                    ],
                    sync_duration_seconds=time.time() - start_time,
                )

            logger.info(
                f"Syncing artifacts to Google Drive: {course_name}/Week_{week_number:02d}"
            )

            # Sync transcript
            success = self._sync_single_file(
                transcript_path,
                target_folder / "transcript.txt",
                "transcript",
                errors,
            )
            if success:
                synced_files += 1
                total_size_bytes += Path(transcript_path).stat().st_size
            else:
                failed_files += 1

            # Sync audio
            success = self._sync_single_file(
                audio_path,
                target_folder / "audio.m4a",
                "audio",
                errors,
            )
            if success:
                synced_files += 1
                total_size_bytes += Path(audio_path).stat().st_size
            else:
                failed_files += 1

            # Sync slides
            success = self._sync_single_file(
                slides_text_path,
                target_folder / "slides.txt",
                "slides",
                errors,
            )
            if success:
                synced_files += 1
                total_size_bytes += Path(slides_text_path).stat().st_size
            else:
                failed_files += 1

            # Build summary
            duration = time.time() - start_time
            result_success = failed_files == 0

            if result_success:
                total_mb = total_size_bytes / (1024 * 1024)
                logger.info(
                    f"✓ Google Drive sync complete: {synced_files} files, {total_mb:.2f} MB"
                )
            else:
                logger.warning(
                    f"✗ Google Drive sync partial failure: {synced_files}/{synced_files + failed_files} files synced"
                )
                for error in errors:
                    logger.error(
                        f"  - {error.file}: {error.error}. Recovery: {error.recovery_action}"
                    )

            return SyncResult(
                success=result_success,
                synced_files=synced_files,
                failed_files=failed_files,
                total_size_bytes=total_size_bytes,
                errors=errors,
                sync_duration_seconds=duration,
            )

        except Exception as e:
            logger.error(
                f"Unexpected error during Google Drive sync: {e}",
                extra={"stage": "gdrive-sync"},
            )
            return SyncResult(
                success=False,
                synced_files=synced_files,
                failed_files=3 - synced_files,
                total_size_bytes=total_size_bytes,
                errors=[
                    SyncError(
                        file="sync-operation",
                        error=f"Unexpected error: {str(e)}",
                        recovery_action="Check error logs and retry sync",
                    )
                ],
                sync_duration_seconds=time.time() - start_time,
            )

    def _sync_single_file(
        self,
        source_path: str,
        target_path: Path,
        file_label: str,
        errors: List[SyncError],
    ) -> bool:
        """
        Sync a single file with error handling and validation.

        Args:
            source_path: Path to source file
            target_path: Path to target location
            file_label: Label for logging (e.g., "transcript")
            errors: List to append errors to

        Returns:
            True if successful, False if failed
        """
        try:
            source = Path(source_path)

            # Check source exists
            if not source.exists():
                error_msg = f"Source file not found: {source_path}"
                recovery = "Check pipeline output or rerun processing"
                errors.append(
                    SyncError(
                        file=file_label, error=error_msg, recovery_action=recovery
                    )
                )
                logger.error(f"  ✗ {file_label}: {error_msg}")
                return False

            # Copy file
            try:
                shutil.copy2(source, target_path)
            except PermissionError:
                error_msg = "Permission denied writing to Google Drive folder"
                recovery = "Check Google Drive folder permissions or reconfigure path"
                errors.append(
                    SyncError(
                        file=file_label, error=error_msg, recovery_action=recovery
                    )
                )
                logger.error(f"  ✗ {file_label}: {error_msg}")
                return False
            except OSError as e:
                if "disk full" in str(e).lower() or "no space" in str(e).lower():
                    error_msg = "Google Drive quota exceeded or disk full"
                    recovery = (
                        "Free space in Google Drive or increase quota. "
                        "Retry sync or disable in config."
                    )
                else:
                    error_msg = f"Copy error: {e}"
                    recovery = "Check Google Drive folder or retry sync"
                errors.append(
                    SyncError(
                        file=file_label, error=error_msg, recovery_action=recovery
                    )
                )
                logger.error(f"  ✗ {file_label}: {error_msg}")
                return False

            # Validate copy
            valid, validate_error = self.validate_file_copy(
                str(source), str(target_path)
            )
            if not valid:
                error_msg = f"Validation failed: {validate_error}"
                recovery = "Retry sync or check Google Drive folder access"
                errors.append(
                    SyncError(
                        file=file_label, error=error_msg, recovery_action=recovery
                    )
                )
                logger.error(f"  ✗ {file_label}: {error_msg}")
                # Clean up partial file
                try:
                    target_path.unlink()
                except:
                    pass
                return False

            # Success
            file_size_mb = source.stat().st_size / (1024 * 1024)
            logger.info(
                f"  ✓ Synced {file_label} ({file_size_mb:.2f} MB) → {target_path}"
            )
            return True

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            recovery = "Check error logs and retry sync"
            errors.append(
                SyncError(file=file_label, error=error_msg, recovery_action=recovery)
            )
            logger.error(f"  ✗ {file_label}: {error_msg}")
            return False
