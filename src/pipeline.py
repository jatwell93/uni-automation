"""
Pipeline orchestration for Phase 2→Phase 3 workflow with error recovery.

Coordinates transcript loading, slide text loading, LLM generation, and Obsidian output.
Implements intelligent retry logic for transient errors (network, API, etc.).
"""

import logging
import time
from pathlib import Path
from typing import Tuple, Callable, Any

from src.config import ConfigModel
from src.llm_generator import LLMGenerator
from src.obsidian_writer import ObsidianWriter
from src.cost_tracker import CostTracker
from src.transcript_processor import PIIDetector
from src.temp_manager import TempFileManager
from src.error_handler import ErrorHandler
from src.logger import get_logger

logger = get_logger(__name__, stage_name="pipeline")


def run_stage(
    stage_func: Callable, stage_name: str, config: ConfigModel, *args, **kwargs
) -> Tuple[bool, Any, str]:
    """
    Execute a pipeline stage with intelligent retry logic for transient errors.

    Args:
        stage_func: Function to execute (e.g., llm_generator.generate_notes)
        stage_name: Name of stage for logging and error categorization
        config: ConfigModel instance
        *args: Positional arguments for stage_func
        **kwargs: Keyword arguments for stage_func

    Returns:
        Tuple of (success: bool, result: Any, message: str)
    """
    max_retries = 3
    logger.set_stage(stage_name)

    for attempt in range(max_retries):
        try:
            result = stage_func(config, *args, **kwargs)
            logger.info(f"✓ {stage_name} completed")
            return (True, result, "")
        except Exception as e:
            should_retry, delay_sec = ErrorHandler.handle_error(
                e, stage_name, max_retries, attempt
            )

            if should_retry:
                error_type = type(e).__name__
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {error_type} - {str(e)[:100]}. "
                    f"Retrying in {delay_sec:.1f}s...",
                    recovery_action=f"Retrying {stage_name}",
                )
                time.sleep(delay_sec)
            else:
                recovery_action = ErrorHandler.get_recovery_action(e)
                logger.error(
                    f"Fatal error in {stage_name}: {type(e).__name__} - {str(e)}",
                    recovery_action=recovery_action,
                    exception=e,
                )
                return (False, None, recovery_action)

    # Max retries exceeded (shouldn't reach here with current logic)
    logger.error(
        f"Max retries ({max_retries}) exceeded for {stage_name}",
        recovery_action=f"Increase max_retries or manually retry {stage_name}",
    )
    return (False, None, "Max retries exceeded")


def run_lecture_pipeline(config: ConfigModel) -> Tuple[bool, str]:
    """
    Orchestrate Phase 2→Phase 3 workflow.

    Coordinates:
    1. Load transcript (from Phase 2 output)
    2. Load slide text (from Phase 2 output)
    3. Detect and remove PII from transcript (Plan 04-03)
    4. Generate notes via LLMGenerator (Plan 03-01)
    5. Write notes via ObsidianWriter (Plan 03-02)
    6. Track costs and print summary
    7. Clean up all temporary files (Plan 04-03)

    Args:
        config: Validated ConfigModel instance

    Returns:
        Tuple of (success, summary_message)
    """
    temp_manager = TempFileManager.instance()

    try:
        # Initialize components
        llm_generator = LLMGenerator(
            api_key=config.openrouter_api_key,
            model=config.llm_model,
            budget_aud=config.llm_budget_aud,
            safety_buffer=config.llm_safety_buffer,
        )

        obsidian_writer = ObsidianWriter(
            {
                "obsidian_vault_path": config.obsidian_vault_path,
                "obsidian_note_subfolder": config.obsidian_note_subfolder,
            }
        )

        cost_tracker = CostTracker()

        # Load transcript and slides from Phase 2 output
        output_dir = Path(config.paths.output_dir)
        transcript_path = output_dir / "transcript.txt"
        slides_path = output_dir / "slides.txt"

        # Check if files exist
        if not transcript_path.exists():
            return (
                False,
                f"Transcript not found at {transcript_path}. Run Phase 2 first.",
            )

        slides_text = ""
        if slides_path.exists():
            slides_text = slides_path.read_text(encoding="utf-8")

        transcript_text = transcript_path.read_text(encoding="utf-8")

        # Detect PII in transcript (Plan 04-03)
        logger.info("Scanning transcript for PII...")
        pii_result = PIIDetector.detect_pii(transcript_text)
        PIIDetector.log_pii_findings(pii_result, config)

        # Remove PII if enabled in config
        if config.remove_pii_from_transcript and pii_result.total_found > 0:
            logger.info("Removing PII from transcript...")
            transcript_text = PIIDetector.remove_pii(transcript_text)
            logger.info("✓ PII removed from transcript before LLM call")

        # Generate notes via LLM
        logger.info("Generating study notes via LLM...")
        llm_result = llm_generator.generate_notes(
            transcript=transcript_text, slides=slides_text
        )

        if not llm_result or llm_result.status != "success":
            error_msg = (
                llm_result.error_message
                if llm_result
                else "Unknown LLM generation error"
            )
            return (False, f"LLM generation failed: {error_msg}")

        # Log cost
        cost_tracker.log_lecture(
            lecture=f"Week {config.metadata.week_number}",
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            model=config.llm_model,
            cost_aud=llm_result.cost_aud,
        )

        # Prepare metadata for Obsidian
        metadata = {
            "course": config.metadata.course_name,
            "week": config.metadata.week_number,
            "date": config.metadata.timestamp or "",
            "panopto_url": config.lecture.url,
            "subfolder": config.obsidian_note_subfolder,
        }

        # Write to Obsidian vault
        logger.info(
            f"Writing notes to Obsidian vault at {config.obsidian_vault_path}..."
        )
        success, result = obsidian_writer.write_complete_note(
            metadata, llm_result.content
        )

        if not success:
            return (False, f"Failed to write notes: {result}")

        # Build summary message
        summary = f"""
✓ Lecture processing complete!

📝 Notes saved to: {result}
💰 Cost: AUD ${llm_result.cost_aud:.4f}
📊 Tokens: {llm_result.input_tokens} input, {llm_result.output_tokens} output

Next: Open Obsidian vault to review notes
"""

        logger.info(summary)
        return (True, summary)

    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)

    finally:
        # Cleanup all temporary files (runs on success and failure)
        logger.info("Cleaning up temporary files...")
        cleanup_summary = temp_manager.cleanup_all()
        logger.info(
            f"✓ Cleanup complete: {cleanup_summary['deleted_count']} files removed"
        )
        if cleanup_summary["failed_count"] > 0:
            logger.warning(
                f"⚠ Failed to delete {cleanup_summary['failed_count']} files "
                "(check permissions). Manually delete temp files if needed."
            )
