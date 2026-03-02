"""
Pipeline orchestration for Phase 2→Phase 3 workflow.

Coordinates transcript loading, slide text loading, LLM generation, and Obsidian output.
"""

import logging
from pathlib import Path
from typing import Tuple

from src.config import ConfigModel
from src.llm_generator import LLMGenerator
from src.obsidian_writer import ObsidianWriter
from src.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


def run_lecture_pipeline(config: ConfigModel) -> Tuple[bool, str]:
    """
    Orchestrate Phase 2→Phase 3 workflow.

    Coordinates:
    1. Load transcript (from Phase 2 output)
    2. Load slide text (from Phase 2 output)
    3. Generate notes via LLMGenerator (Plan 03-01)
    4. Write notes via ObsidianWriter (Plan 03-02)
    5. Track costs and print summary

    Args:
        config: Validated ConfigModel instance

    Returns:
        Tuple of (success, summary_message)
    """
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
