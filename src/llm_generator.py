"""
LLM Generator module for creating study notes from transcripts and slides.

Includes token counting, budget validation, transcript truncation, and API integration.
"""

import logging
import tiktoken
from typing import Tuple

# Configure logging
logger = logging.getLogger(__name__)


class TokenCounter:
    """Count tokens in text using tiktoken encoding."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        """Initialize token counter with specified encoding."""
        self.encoding_name = encoding_name
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def estimate_cost(
        self,
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


class BudgetValidator:
    """Validate token budgets against cost limits."""

    def __init__(self):
        """Initialize budget validator."""
        self.token_counter = TokenCounter()

    def validate_token_budget(
        self,
        input_tokens: int,
        budget_aud: float = 0.30,
        model: str = "deepseek/deepseek-chat",
        safety_buffer: float = 0.20,
    ) -> Tuple[bool, str]:
        """
        Validate token count against budget with safety buffer.

        Args:
            input_tokens: Number of input tokens
            budget_aud: Maximum budget in AUD (default 0.30)
            model: Model to use for cost estimation
            safety_buffer: Safety buffer as percentage (default 0.20 = 20%)

        Returns:
            Tuple of (passes_budget: bool, reason_message: str)
        """
        # Estimate output tokens (typical response ~600 tokens)
        estimated_output = 600

        # Calculate estimated cost
        estimated_cost = self.token_counter.estimate_cost(
            input_tokens, estimated_output, model
        )

        # Apply safety buffer to budget
        effective_budget = budget_aud * (1 - safety_buffer)

        if estimated_cost <= effective_budget:
            remaining = effective_budget - estimated_cost
            return (
                True,
                f"✓ Token budget OK. Input: {input_tokens:,} tokens, "
                f"Est. cost: AUD ${estimated_cost:.4f}, Remaining: AUD ${remaining:.4f}",
            )
        else:
            overage = estimated_cost - effective_budget
            return (
                False,
                f"✗ Token budget exceeded. Input: {input_tokens:,} tokens, "
                f"Est. cost: AUD ${estimated_cost:.4f}, Overage: AUD ${overage:.4f}. "
                f"Consider shorter lectures or using Haiku model.",
            )


class TranscriptTruncator:
    """Intelligently truncate transcripts to fit token budgets."""

    def __init__(self):
        """Initialize transcript truncator."""
        self.token_counter = TokenCounter()

    def truncate_transcript(self, text: str, target_tokens: int = 3000) -> str:
        """
        Intelligently reduce transcript to target token count.

        Uses two strategies:
        1. Sampling: Remove every Nth line to reduce tokens
        2. Halving: Take first 50% of content by token count

        Args:
            text: Transcript text to truncate
            target_tokens: Target token count (default 3000)

        Returns:
            Truncated transcript text
        """
        current_tokens = self.token_counter.count_tokens(text)

        # If already under budget, return unchanged
        if current_tokens <= target_tokens:
            logger.info(f"Transcript within budget ({current_tokens:,} tokens)")
            return text

        lines = text.split("\n")
        logger.info(f"Truncating {current_tokens:,} tokens to {target_tokens:,}")

        # Strategy 1: Sampling - remove every Nth line
        if len(lines) > 1:
            # Calculate sampling rate
            ratio = current_tokens / target_tokens
            sample_rate = max(2, int(ratio))  # Keep at least every other line

            sampled_lines = []
            for i, line in enumerate(lines):
                if i % sample_rate == 0:
                    sampled_lines.append(line)

            sampled_text = "\n".join(sampled_lines)
            sampled_tokens = self.token_counter.count_tokens(sampled_text)

            logger.info(
                f"Strategy 1 (sampling every {sample_rate} lines): {sampled_tokens:,} tokens"
            )

            if sampled_tokens <= target_tokens:
                return sampled_text

        # Strategy 2: Halving - take first 50% of content
        # Binary search to find the right cutoff point
        start_idx = 0
        end_idx = len(text)

        while start_idx < end_idx:
            mid_idx = (start_idx + end_idx + 1) // 2
            partial_text = text[:mid_idx]
            partial_tokens = self.token_counter.count_tokens(partial_text)

            if partial_tokens <= target_tokens:
                start_idx = mid_idx
            else:
                end_idx = mid_idx - 1

        halved_text = text[:start_idx]
        halved_tokens = self.token_counter.count_tokens(halved_text)
        logger.info(f"Strategy 2 (binary search): {halved_tokens:,} tokens")

        return halved_text
