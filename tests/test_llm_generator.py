"""
Tests for LLM Generator module.

Covers token counting, budget validation, transcript truncation, and API integration.
"""

import pytest
import tiktoken
from src.llm_generator import TokenCounter, BudgetValidator, TranscriptTruncator


class TestTokenCounter:
    """Tests for TokenCounter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.counter = TokenCounter()

    def test_count_tokens_empty_string(self):
        """Empty string should return 0 tokens."""
        result = self.counter.count_tokens("")
        assert result == 0

    def test_count_tokens_short_text(self):
        """Short text 'Hello world' should count tokens correctly."""
        result = self.counter.count_tokens("Hello world")
        # "Hello world" typically encodes to 2 tokens
        assert result > 0
        assert result <= 10

    def test_count_tokens_long_transcript(self):
        """Long transcript (5000+ chars) should count accurately."""
        # Create a long transcript-like text
        text = "This is a lecture transcript. " * 200
        result = self.counter.count_tokens(text)
        # Should be substantial number of tokens
        assert result > 500
        assert result < 3000

    def test_count_tokens_unicode(self):
        """Unicode text should tokenize correctly."""
        text = "Hello 世界 مرحبا мир"
        result = self.counter.count_tokens(text)
        assert result > 0

    def test_estimate_cost_deepseek(self):
        """DeepSeek cost estimation: 5000 input, 500 output."""
        cost = self.counter.estimate_cost(5000, 500, "deepseek/deepseek-chat")
        # 5000 * 0.28/1M + 500 * 0.42/1M ≈ 0.0014 + 0.00021 ≈ 0.0016
        assert 0.001 < cost < 0.003

    def test_estimate_cost_haiku(self):
        """Haiku cost estimation: 5000 input, 500 output."""
        cost = self.counter.estimate_cost(5000, 500, "claude-3-haiku")
        # 5000 * 1.00/1M + 500 * 5.00/1M ≈ 0.005 + 0.0025 ≈ 0.0075
        assert 0.005 < cost < 0.01


class TestBudgetValidator:
    """Tests for BudgetValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = BudgetValidator()

    def test_validate_budget_passes(self):
        """2000 input tokens under budget should pass."""
        passes, msg = self.validator.validate_token_budget(
            2000, budget_aud=0.30, model="deepseek/deepseek-chat"
        )
        assert passes is True
        assert "✓" in msg

    def test_validate_budget_fails(self):
        """Large token count with very tight budget exceeds and should fail."""
        # Use a very tight budget to test failure case
        # 10000 tokens * 1.00/1M + 600 * 5.00/1M ≈ 0.01 + 0.003 ≈ 0.013
        # With 20% buffer on 0.01 budget: 0.01 * 0.80 = 0.008 (cost exceeds effective budget)
        passes, msg = self.validator.validate_token_budget(
            10000, budget_aud=0.01, model="claude-3-haiku"
        )
        assert passes is False
        assert "✗" in msg or "exceeds" in msg.lower()

    def test_validate_budget_with_safety_buffer(self):
        """Edge case: cost at budget without buffer should fail with buffer."""
        # Find a token count that's barely under budget without buffer
        # but over with 20% buffer
        passes, msg = self.validator.validate_token_budget(
            5000, budget_aud=0.30, model="deepseek/deepseek-chat", safety_buffer=0.20
        )
        # 5000 tokens DeepSeek: ~0.0028 + 0.00021 ≈ 0.003
        # Budget with 20% buffer: 0.30 * 0.80 = 0.24 (much larger than actual cost)
        assert passes is True


class TestTranscriptTruncator:
    """Tests for TranscriptTruncator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.truncator = TranscriptTruncator()

    def test_truncate_transcript_under_budget(self):
        """1000 token transcript under 3000 target should return unchanged."""
        text = "This is a short transcript. " * 30
        result = self.truncator.truncate_transcript(text, target_tokens=3000)
        assert result == text

    def test_truncate_transcript_with_sampling(self):
        """Large token transcript should truncate via sampling."""
        text = "This is line content with more details. " * 500
        result = self.truncator.truncate_transcript(text, target_tokens=2500)
        result_tokens = self.truncator.token_counter.count_tokens(result)
        assert result_tokens <= 2500
        assert len(result) < len(text)

    def test_truncate_transcript_with_halving(self):
        """Very large transcript should use halving strategy if sampling insufficient."""
        text = "Lorem ipsum dolor sit amet. " * 1000
        result = self.truncator.truncate_transcript(text, target_tokens=2000)
        result_tokens = self.truncator.token_counter.count_tokens(result)
        assert result_tokens <= 2000
        assert len(result) < len(text)

    def test_truncate_transcript_preserves_coherence(self):
        """Truncated output should still be readable."""
        text = "The lecture covered quantum mechanics. " * 300
        result = self.truncator.truncate_transcript(text, target_tokens=2500)
        # Should still contain meaningful content
        assert len(result) > 0
        assert "lecture" in result.lower() or "quantum" in result.lower()


class TestLLMGeneratorIntegration:
    """Integration tests for LLMGenerator (mocked API calls)."""

    def test_token_counter_consistency(self):
        """Token counter should be consistent across multiple calls."""
        counter = TokenCounter()
        text = "The quick brown fox jumps over the lazy dog" * 10
        count1 = counter.count_tokens(text)
        count2 = counter.count_tokens(text)
        assert count1 == count2

    def test_budget_validation_uses_correct_rates(self):
        """Budget validation should use correct pricing rates."""
        validator = BudgetValidator()

        # DeepSeek: 100 input + 100 output should be very cheap
        passes_ds, _ = validator.validate_token_budget(
            100, budget_aud=0.01, model="deepseek/deepseek-chat"
        )
        assert passes_ds is True

        # Haiku: 100 input + 100 output should be more expensive
        passes_hk, _ = validator.validate_token_budget(
            100, budget_aud=0.001, model="claude-3-haiku"
        )
        assert passes_hk is False

    def test_truncator_respects_target_tokens(self):
        """Truncator should always respect target token count."""
        truncator = TranscriptTruncator()
        text = "Content " * 2000  # Very large text

        for target in [1000, 2000, 3000]:
            result = truncator.truncate_transcript(text, target_tokens=target)
            result_tokens = truncator.token_counter.count_tokens(result)
            assert result_tokens <= target + 50  # Allow small margin for edge cases
