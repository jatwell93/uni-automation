"""
Cost tracking module for monitoring LLM API costs and enforcing budgets.

Tracks per-lecture costs, maintains weekly summaries, and alerts on budget overages.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "deepseek/deepseek-chat",
) -> float:
    """
    Estimate cost in AUD based on token counts and model.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model identifier (deepseek/deepseek-chat or claude-3-haiku)

    Returns:
        Estimated cost in AUD
    """
    # Pricing from OpenRouter (per 1M tokens)
    if "deepseek" in model.lower():
        input_rate = 0.28 / 1_000_000  # AUD per token
        output_rate = 0.42 / 1_000_000
    elif "haiku" in model.lower():
        input_rate = 1.00 / 1_000_000
        output_rate = 5.00 / 1_000_000
    else:
        # Default to DeepSeek
        input_rate = 0.28 / 1_000_000
        output_rate = 0.42 / 1_000_000

    total_cost = (input_tokens * input_rate) + (output_tokens * output_rate)
    return round(total_cost, 6)


def format_cost_estimate(
    input_tokens: int, model: str = "deepseek/deepseek-chat", budget_aud: float = 0.30
) -> str:
    """
    Format a cost estimate for display.

    Args:
        input_tokens: Number of input tokens
        model: Model identifier
        budget_aud: Budget in AUD

    Returns:
        Formatted string with cost estimate and budget info
    """
    estimated_output = 600
    estimated_cost = estimate_cost(input_tokens, estimated_output, model)
    budget_remaining = budget_aud - estimated_cost

    return f"""📊 Cost Estimate:
  Input tokens: {input_tokens:,}
  Estimated output: {estimated_output}
  Model: {model}
  Estimated cost: AUD ${estimated_cost:.4f}
  Budget remaining: AUD ${budget_remaining:.4f}"""


class CostTracker:
    """Track lecture costs and enforce budget limits."""

    def __init__(self, log_file: Path = Path("cost_tracking.json")):
        """
        Initialize cost tracker.

        Args:
            log_file: Path to JSON log file (default: cost_tracking.json)
        """
        self.log_file = log_file
        self.data = self.load()

    def load(self) -> dict:
        """
        Load existing cost log from disk.

        Returns JSON dict with 'lectures' list and 'weekly_total'. Creates empty
        if file doesn't exist.
        """
        if self.log_file.exists():
            try:
                with open(self.log_file, "r") as f:
                    data = json.load(f)
                logger.info(
                    f"Loaded {len(data.get('lectures', []))} lectures from cost log"
                )
                return data
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse cost log: {e}. Starting fresh.")
                return {"lectures": [], "weekly_total": 0.0}
        else:
            return {"lectures": [], "weekly_total": 0.0}

    def save(self) -> None:
        """Persist cost data to JSON file."""
        with open(self.log_file, "w") as f:
            json.dump(self.data, f, indent=2)
        logger.info(f"Saved cost tracking data to {self.log_file}")

    def log_lecture(
        self,
        lecture_name: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        cost_aud: float,
    ) -> None:
        """
        Log a lecture's cost.

        Args:
            lecture_name: Name/ID of lecture
            input_tokens: Input token count
            output_tokens: Output token count
            model: Model used
            cost_aud: Cost in AUD
        """
        entry = {
            "lecture": lecture_name,
            "timestamp": datetime.now().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
            "cost_aud": cost_aud,
        }
        self.data["lectures"].append(entry)
        self.data["weekly_total"] += cost_aud
        self.save()
        logger.info(f"Logged lecture: {lecture_name}, cost: AUD ${cost_aud:.4f}")

    def get_weekly_total(self) -> float:
        """Return total cost for week."""
        return self.data["weekly_total"]

    def get_lecture_count(self) -> int:
        """Return number of lectures logged."""
        return len(self.data["lectures"])

    def alert_if_over_budget(
        self, cost_aud: float, budget_aud: float = 0.50
    ) -> Tuple[bool, str]:
        """
        Check if single lecture exceeds budget.

        Args:
            cost_aud: Cost in AUD
            budget_aud: Budget limit in AUD (default 0.50)

        Returns:
            Tuple of (is_over: bool, message: str)
        """
        if cost_aud > budget_aud:
            overage = cost_aud - budget_aud
            return (
                True,
                f"⚠️  Lecture exceeded budget: AUD ${cost_aud:.2f} > ${budget_aud:.2f} (overage: ${overage:.2f})",
            )
        else:
            return (
                False,
                f"✓ Lecture within budget: AUD ${cost_aud:.2f} <= ${budget_aud:.2f}",
            )

    def alert_if_weekly_over_budget(self, budget_aud: float = 3.00) -> Tuple[bool, str]:
        """
        Check if weekly total exceeds budget.

        Args:
            budget_aud: Weekly budget limit in AUD (default 3.00)

        Returns:
            Tuple of (is_over: bool, message: str)
        """
        total = self.get_weekly_total()
        if total > budget_aud:
            overage = total - budget_aud
            return (
                True,
                f"⚠️  Weekly budget exceeded: AUD ${total:.2f} > ${budget_aud:.2f} (overage: ${overage:.2f})",
            )
        else:
            remaining = budget_aud - total
            return (
                False,
                f"✓ Weekly budget OK: AUD ${total:.2f} <= ${budget_aud:.2f} (remaining: ${remaining:.2f})",
            )

    def format_weekly_summary(self) -> str:
        """
        Format weekly cost summary with box drawing.

        Returns:
            Formatted string with summary table and optional warning
        """
        lectures = self.data.get("lectures", [])
        total = self.get_weekly_total()
        count = len(lectures)

        if count > 0:
            average = total / count
        else:
            average = 0.0

        budget = 3.00  # Default weekly budget
        remaining = budget - total

        # Build summary with box drawing (ASCII for cross-platform)
        summary = "╔════════════════════════════════════╗\n"
        summary += "║       WEEKLY COST SUMMARY          ║\n"
        summary += "╠════════════════════════════════════╣\n"
        summary += f"║ Lectures processed: {count:<18} ║\n"
        summary += f"║ Total cost: AUD ${total:<25.2f}║\n"
        summary += f"║ Average per lecture: AUD ${average:<16.2f}║\n"
        summary += f"║ Budget (4 lectures): AUD ${budget:<15.2f}║\n"
        summary += f"║ Remaining: AUD ${remaining:<24.2f}║\n"
        summary += "╚════════════════════════════════════╝"

        # Add warning if over budget
        if total > budget:
            overage = total - budget
            summary += f"\n\n⚠️  WARNING: Over budget by AUD ${overage:.2f}"

        return summary

    def reset_weekly(self) -> None:
        """Clear weekly log and reset total."""
        self.data["lectures"] = []
        self.data["weekly_total"] = 0.0
        self.save()
        logger.info("Reset weekly cost tracking")
