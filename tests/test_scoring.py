"""Tests for the end-to-end scoring engine and trace loading."""

import json
from pathlib import Path

import pytest

from agentlint.scoring import lint_trace

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestLintTrace:
    def test_healthy_trace_high_score(self):
        """A healthy trace should score above 0.7."""
        result = lint_trace(FIXTURES_DIR / "healthy_trace_01.json")
        assert result.score >= 0.7, f"Healthy trace scored too low: {result.score}"
        assert result.error_count == 0
        assert result.num_steps == 6

    def test_looping_trace_has_findings(self):
        """A looping trace should have cycle detection findings."""
        result = lint_trace(FIXTURES_DIR / "looping_trace_01.json")
        assert len(result.findings) > 0
        analyzer_names = {f.analyzer for f in result.findings}
        # Should detect at least cycles or tool efficiency issues
        assert len(analyzer_names) >= 1

    def test_hallucinating_trace_detected(self):
        """A trace with hallucinated tools should be flagged."""
        result = lint_trace(FIXTURES_DIR / "hallucinating_trace_01.json")
        hallucination_findings = [
            f for f in result.findings if f.analyzer == "hallucination-signals"
        ]
        assert len(hallucination_findings) > 0
        # Should detect the made-up tool names
        assert any("search_files" in f.message or "execute_sql" in f.message
                    for f in hallucination_findings)

    def test_analysis_time_is_fast(self):
        """Analysis should complete in under 500ms."""
        result = lint_trace(FIXTURES_DIR / "healthy_trace_01.json")
        assert result.analysis_time_ms < 500, (
            f"Analysis took {result.analysis_time_ms}ms — should be under 500ms"
        )

    def test_lint_trace_with_trace_object(self):
        """Should accept a Trace object directly."""
        from agentlint.schema import Step, StepType, Trace

        trace = Trace(
            trace_id="inline-test",
            steps=[
                Step(index=0, step_type=StepType.THOUGHT, content="Test"),
                Step(index=1, step_type=StepType.ACTION, content="Done"),
            ],
        )
        result = lint_trace(trace)
        assert result.score >= 0.0
        assert result.trace_id == "inline-test"

    def test_file_not_found_raises(self):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            lint_trace("nonexistent_trace.json")

    def test_result_passed_property(self):
        """The passed property should reflect error presence."""
        result = lint_trace(FIXTURES_DIR / "healthy_trace_01.json")
        assert result.passed  # Healthy trace should pass

    def test_json_serializable(self):
        """LintResult should be JSON-serializable."""
        result = lint_trace(FIXTURES_DIR / "healthy_trace_01.json")
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert "score" in parsed
        assert "findings" in parsed
