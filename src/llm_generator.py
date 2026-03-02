"""
LLM Generator module for creating study notes from transcripts and slides.

Includes token counting, budget validation, transcript truncation, and API integration.
"""

import logging
import tiktoken
from typing import Tuple, Optional, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from openai import OpenAI, RateLimitError, APIError
from src.models import LLMResult

# Configure logging
logger = logging.getLogger(__name__)

# System prompt for study note generation
SYSTEM_PROMPT = """You are an expert study note generator. Your goal is to create clear, structured study notes from lecture transcripts and slides.

INSTRUCTIONS:
1. Simplify complex concepts using analogies and plain language
2. Highlight what students actually need to know
3. Be concise: avoid padding, keep content high-value
4. Flag weak areas in the transcript (indicate "⚠️ Low confidence" sections)

OUTPUT FORMAT:
Generate exactly 6 sections below. Use markdown with clear headers.

## Summary
[2-3 sentences: What is this lecture about?]

## Key Concepts
[Bullet list: 5-8 core ideas. One sentence each. Order by importance.]

## Examples
[3-5 real-world or concrete examples. Show how concepts apply.]

## Formulas & Key Equations
[If applicable: definitions, formulas, key numbers. Use LaTeX for math.]

## Pitfalls & Common Mistakes
[What students often get wrong. What to watch out for.]

## Review Questions
[5-7 self-test questions. Answering these = proof of understanding.]

CONSTRAINTS:
- Assume reader has no prior knowledge of this topic
- Flag sections with unclear/missing explanations
- Total output: 800–1200 words
- Markdown-valid formatting (valid for Obsidian rendering)
"""


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


class LLMGenerator:
    """Generate study notes from transcripts and slides via OpenRouter API."""

    def __init__(self, config: dict):
        """
        Initialize LLM generator with OpenRouter API configuration.

        Args:
            config: Configuration dict with 'openrouter_api_key'
        """
        self.config = config
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.get("openrouter_api_key"),
        )
        self.token_counter = TokenCounter()
        self.budget_validator = BudgetValidator()
        self.truncator = TranscriptTruncator()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    def _call_llm_with_retry(
        self, model: str, messages: List[dict], max_tokens: int = 1500
    ) -> str:
        """
        Call LLM API with automatic retry logic.

        Uses exponential backoff for rate limits and API errors.
        401 (auth) errors will raise immediately without retry.

        Args:
            model: Model identifier
            messages: List of message dicts with role and content
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response

        Raises:
            APIError: On non-retryable API errors
            RateLimitError: On rate limits (will retry)
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except APIError as e:
            # Check for auth error (401) - fail immediately
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error(f"Invalid OpenRouter API key: {e}")
                raise
            # Other API errors will be retried by decorator
            logger.warning(f"API error (will retry): {e}")
            raise
        except RateLimitError as e:
            logger.warning(f"Rate limited (will retry): {e}")
            raise

    def generate_notes(
        self, transcript: str, slide_text: str, model: str = "deepseek/deepseek-chat"
    ) -> LLMResult:
        """
        Generate study notes from transcript and slide text.

        Full workflow:
        1. Combine and count tokens
        2. Validate budget
        3. Truncate if necessary
        4. Log estimate
        5. Call LLM API
        6. Track cost

        Args:
            transcript: Lecture transcript text
            slide_text: Extracted slide text
            model: Model to use (default deepseek)

        Returns:
            LLMResult with generated notes, token counts, and costs
        """
        try:
            # Combine transcript and slide text
            combined = f"TRANSCRIPT:\n{transcript}\n\nSLIDE TEXT:\n{slide_text}"

            # Count input tokens (system prompt + combined text)
            system_tokens = self.token_counter.count_tokens(SYSTEM_PROMPT)
            content_tokens = self.token_counter.count_tokens(combined)
            total_input = system_tokens + content_tokens

            logger.info(
                f"Input tokens: {total_input:,} (system: {system_tokens}, content: {content_tokens})"
            )

            # Validate budget
            passes_budget, budget_msg = self.budget_validator.validate_token_budget(
                total_input, budget_aud=0.30, model=model
            )
            logger.info(budget_msg)

            # If over budget, truncate transcript
            if not passes_budget:
                logger.warning("Budget exceeded, truncating transcript...")
                transcript = self.truncator.truncate_transcript(
                    transcript, target_tokens=3000
                )
                combined = f"TRANSCRIPT:\n{transcript}\n\nSLIDE TEXT:\n{slide_text}"
                content_tokens = self.token_counter.count_tokens(combined)
                total_input = system_tokens + content_tokens
                logger.info(f"After truncation: {total_input:,} tokens")

            # Estimate output tokens (typical response)
            estimated_output = 600
            estimated_cost = self.token_counter.estimate_cost(
                total_input, estimated_output, model
            )
            logger.info(f"Estimated cost: AUD ${estimated_cost:.6f}")

            # Call LLM API
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": combined},
            ]

            content = self._call_llm_with_retry(model, messages, max_tokens=1500)

            # Calculate actual cost (use estimated if usage not available)
            actual_output = estimated_output
            actual_cost = estimated_cost

            logger.info(f"Generation successful. Cost: AUD ${actual_cost:.6f}")

            return LLMResult(
                status="success",
                content=content,
                input_tokens=total_input,
                output_tokens=actual_output,
                cost_aud=actual_cost,
            )

        except APIError as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                error_msg = "Invalid OpenRouter API key. Check your configuration."
            else:
                error_msg = f"API error: {str(e)}"
            logger.error(error_msg)
            return LLMResult(
                status="error",
                error_message=error_msg,
            )
        except RateLimitError:
            error_msg = "Rate limited. Retries exhausted. Try again in a few minutes."
            logger.error(error_msg)
            return LLMResult(
                status="error",
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"{error_msg}\n{type(e).__name__}: {e}")
            return LLMResult(
                status="error",
                error_message=error_msg,
            )
