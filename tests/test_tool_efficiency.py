"""Tests for the tool efficiency analyzer."""

from agentlint.analyzers.tool_efficiency import ToolEfficiencyAnalyzer
from agentlint.schema import Severity, Step, StepType, ToolCall, Trace


def _make_trace(steps: list[Step]) -> Trace:
    return Trace(trace_id="test", steps=steps)


def _tool_step(index: int, name: str, args: dict, success: bool = True, result: str = "ok") -> Step:
    return Step(
        index=index,
        step_type=StepType.TOOL_CALL,
        content=f"Calling {name}",
        tool_call=ToolCall(name=name, arguments=args, success=success, result=result),
    )


class TestToolEfficiency:
    def setup_method(self):
        self.analyzer = ToolEfficiencyAnalyzer()

    def test_no_findings_for_efficient_trace(self):
        """All unique tool calls should produce no warnings."""
        trace = _make_trace([
            _tool_step(0, "search", {"q": "python"}),
            _tool_step(1, "read", {"path": "a.py"}),
            _tool_step(2, "write", {"path": "b.py", "content": "hello"}),
        ])
        findings = self.analyzer.analyze(trace)
        # No duplicate calls, so no findings expected
        duplicate_findings = [f for f in findings if "Duplicate" in f.message]
        assert len(duplicate_findings) == 0

    def test_detects_duplicate_tool_calls(self):
        """Exact same tool call repeated should be flagged."""
        trace = _make_trace([
            _tool_step(0, "search", {"q": "python"}),
            _tool_step(1, "search", {"q": "python"}),  # Exact duplicate
            _tool_step(2, "search", {"q": "python"}),  # Another duplicate
        ])
        findings = self.analyzer.analyze(trace)
        duplicate_findings = [f for f in findings if "Duplicate" in f.message]
        assert len(duplicate_findings) >= 2  # Steps 1 and 2 are duplicates

    def test_different_args_not_duplicate(self):
        """Same tool with different arguments is NOT a duplicate."""
        trace = _make_trace([
            _tool_step(0, "search", {"q": "python"}),
            _tool_step(1, "search", {"q": "javascript"}),  # Different query
        ])
        findings = self.analyzer.analyze(trace)
        duplicate_findings = [f for f in findings if "Duplicate" in f.message]
        assert len(duplicate_findings) == 0

    def test_no_tool_calls(self):
        """Trace with no tool calls should produce no findings."""
        trace = _make_trace([
            Step(index=0, step_type=StepType.THOUGHT, content="Thinking..."),
        ])
        findings = self.analyzer.analyze(trace)
        assert len(findings) == 0

    def test_low_efficiency_error(self):
        """Very low efficiency should produce an error-level finding."""
        analyzer = ToolEfficiencyAnalyzer(error_threshold=0.5)
        trace = _make_trace([
            _tool_step(0, "search", {"q": "a"}),
            _tool_step(1, "search", {"q": "a"}),  # dup
            _tool_step(2, "search", {"q": "a"}),  # dup
            _tool_step(3, "search", {"q": "a"}),  # dup
        ])
        findings = analyzer.analyze(trace)
        error_findings = [f for f in findings if f.severity == Severity.ERROR]
        assert len(error_findings) > 0
