"""
Tests for cost tracking module.

Covers cost logging, budget alerts, weekly summaries, and cost estimation.
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.cost_tracker import CostTracker, estimate_cost, format_cost_estimate


class TestCostEstimation:
    """Tests for cost estimation functions."""

    def test_estimate_cost_deepseek(self):
        """DeepSeek cost estimation: 5000 input, 500 output."""
        cost = estimate_cost(5000, 500, "deepseek/deepseek-chat")
        # 5000 * 0.28/1M + 500 * 0.42/1M ≈ 0.0014 + 0.00021 ≈ 0.00161
        assert 0.001 < cost < 0.003

    def test_estimate_cost_haiku(self):
        """Haiku cost estimation: 5000 input, 500 output."""
        cost = estimate_cost(5000, 500, "claude-3-haiku")
        # 5000 * 1.00/1M + 500 * 5.00/1M ≈ 0.005 + 0.0025 ≈ 0.0075
        assert 0.005 < cost < 0.01

    def test_format_cost_estimate(self):
        """Cost estimate should include tokens, model, and budget."""
        output = format_cost_estimate(5000, "deepseek/deepseek-chat", budget_aud=0.30)
        assert "Input tokens:" in output
        assert "Estimated output:" in output
        assert "Model:" in output
        assert "deepseek" in output.lower()
        assert "Cost Estimate:" in output
        assert "Budget remaining:" in output


class TestCostTracker:
    """Tests for CostTracker class."""

    def setup_method(self):
        """Set up test fixtures with temporary file."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.log_path = Path(self.temp_file.name)
        self.tracker = CostTracker(self.log_path)

    def teardown_method(self):
        """Clean up temporary file."""
        if self.log_path.exists():
            self.log_path.unlink()

    def test_log_lecture_single(self):
        """Log a single lecture and verify it's in JSON."""
        self.tracker.log_lecture(
            "Lecture 1", 5000, 500, "deepseek/deepseek-chat", 0.001
        )

        assert self.tracker.get_lecture_count() == 1
        assert len(self.tracker.data["lectures"]) == 1
        assert self.tracker.data["lectures"][0]["lecture"] == "Lecture 1"

    def test_log_lecture_updates_weekly_total(self):
        """Log multiple lectures and verify weekly total."""
        self.tracker.log_lecture(
            "Lecture 1", 5000, 500, "deepseek/deepseek-chat", 0.001
        )
        self.tracker.log_lecture(
            "Lecture 2", 5000, 500, "deepseek/deepseek-chat", 0.001
        )

        assert self.tracker.get_lecture_count() == 2
        assert abs(self.tracker.get_weekly_total() - 0.002) < 0.0001

    def test_alert_over_budget_passes(self):
        """Cost $0.30 vs budget $0.50 should pass."""
        is_over, msg = self.tracker.alert_if_over_budget(0.30, budget_aud=0.50)
        assert is_over is False
        assert "✓" in msg

    def test_alert_over_budget_fails(self):
        """Cost $0.75 vs budget $0.50 should fail with warning."""
        is_over, msg = self.tracker.alert_if_over_budget(0.75, budget_aud=0.50)
        assert is_over is True
        assert "⚠️" in msg or "exceeded" in msg.lower()

    def test_alert_weekly_over_budget_passes(self):
        """Weekly $2.00 vs budget $3.00 should pass."""
        self.tracker.data["weekly_total"] = 2.00
        is_over, msg = self.tracker.alert_if_weekly_over_budget(budget_aud=3.00)
        assert is_over is False
        assert "✓" in msg

    def test_alert_weekly_over_budget_fails(self):
        """Weekly $3.50 vs budget $3.00 should fail with overage."""
        self.tracker.data["weekly_total"] = 3.50
        is_over, msg = self.tracker.alert_if_weekly_over_budget(budget_aud=3.00)
        assert is_over is True
        assert "⚠️" in msg or "exceeded" in msg.lower()

    def test_format_weekly_summary_single_lecture(self):
        """Single lecture should appear in summary."""
        self.tracker.log_lecture(
            "Lecture 1", 5000, 500, "deepseek/deepseek-chat", 0.001
        )
        summary = self.tracker.format_weekly_summary()

        assert "WEEKLY COST SUMMARY" in summary
        assert "Lectures processed: 1" in summary
        assert "AUD" in summary

    def test_format_weekly_summary_with_warning(self):
        """Weekly total over budget should include warning."""
        # Manually set total over budget
        self.tracker.data["weekly_total"] = 3.50
        self.tracker.data["lectures"] = [
            {
                "lecture": "L1",
                "timestamp": "2026-03-02T10:00:00",
                "input_tokens": 5000,
                "output_tokens": 500,
                "model": "deepseek/deepseek-chat",
                "cost_aud": 0.001,
            },
            {
                "lecture": "L2",
                "timestamp": "2026-03-02T11:00:00",
                "input_tokens": 5000,
                "output_tokens": 500,
                "model": "deepseek/deepseek-chat",
                "cost_aud": 0.001,
            },
            {
                "lecture": "L3",
                "timestamp": "2026-03-02T12:00:00",
                "input_tokens": 5000,
                "output_tokens": 500,
                "model": "deepseek/deepseek-chat",
                "cost_aud": 0.001,
            },
            {
                "lecture": "L4",
                "timestamp": "2026-03-02T13:00:00",
                "input_tokens": 5000,
                "output_tokens": 500,
                "model": "deepseek/deepseek-chat",
                "cost_aud": 0.001,
            },
        ]

        summary = self.tracker.format_weekly_summary()
        assert "WARNING" in summary
        assert "over budget" in summary.lower()

    def test_load_existing_log(self):
        """Load existing JSON log from file."""
        # Create initial log
        self.tracker.log_lecture(
            "Lecture 1", 5000, 500, "deepseek/deepseek-chat", 0.001
        )

        # Load fresh tracker from same file
        new_tracker = CostTracker(self.log_path)
        assert new_tracker.get_lecture_count() == 1
        assert new_tracker.get_lecture_count() == self.tracker.get_lecture_count()

    def test_reset_weekly(self):
        """Reset should clear lectures and total."""
        self.tracker.log_lecture(
            "Lecture 1", 5000, 500, "deepseek/deepseek-chat", 0.001
        )
        assert self.tracker.get_lecture_count() == 1

        self.tracker.reset_weekly()
        assert self.tracker.get_lecture_count() == 0
        assert self.tracker.get_weekly_total() == 0.0


class TestCostTrackerIntegration:
    """Integration tests for cost tracking workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.log_path = Path(self.temp_file.name)
        self.tracker = CostTracker(self.log_path)

    def teardown_method(self):
        """Clean up."""
        if self.log_path.exists():
            self.log_path.unlink()

    def test_full_week_tracking(self):
        """Track a full week of lectures."""
        lectures = [
            ("Week5-Lecture1", 5000, 500, "deepseek/deepseek-chat", 0.0016),
            ("Week5-Lecture2", 4500, 400, "deepseek/deepseek-chat", 0.0014),
            ("Week5-Lecture3", 6000, 600, "deepseek/deepseek-chat", 0.0019),
            ("Week5-Lecture4", 5500, 550, "deepseek/deepseek-chat", 0.0017),
        ]

        for name, inp, out, model, cost in lectures:
            self.tracker.log_lecture(name, inp, out, model, cost)

        assert self.tracker.get_lecture_count() == 4
        expected_total = sum(c[4] for c in lectures)
        assert abs(self.tracker.get_weekly_total() - expected_total) < 0.0001

        # Should be well under budget
        is_over, _ = self.tracker.alert_if_weekly_over_budget(budget_aud=3.00)
        assert is_over is False

    def test_cost_estimation_matches_tracking(self):
        """Estimated cost should match tracked cost."""
        input_tokens = 5000
        output_tokens = 500

        estimated = estimate_cost(input_tokens, output_tokens, "deepseek/deepseek-chat")
        self.tracker.log_lecture(
            "Test", input_tokens, output_tokens, "deepseek/deepseek-chat", estimated
        )

        assert len(self.tracker.data["lectures"]) == 1
        logged_cost = self.tracker.data["lectures"][0]["cost_aud"]
        assert logged_cost == estimated
