"""Tests for the cycle detector analyzer."""

from agentlint.analyzers.cycle_detector import CycleDetector
from agentlint.schema import Severity, Step, StepType, ToolCall, Trace


def _make_trace(steps: list[Step], **kwargs) -> Trace:
    """Helper to create a trace with the given steps."""
    return Trace(trace_id="test", steps=steps, **kwargs)


def _tool_step(index: int, name: str, args: dict | None = None) -> Step:
    """Helper to create a tool call step."""
    return Step(
        index=index,
        step_type=StepType.TOOL_CALL,
        content=f"Calling {name}",
        tool_call=ToolCall(name=name, arguments=args or {}, success=True),
    )


def _thought_step(index: int, content: str) -> Step:
    """Helper to create a thought step."""
    return Step(index=index, step_type=StepType.THOUGHT, content=content)


class TestCycleDetector:
    def setup_method(self):
        self.analyzer = CycleDetector()

    def test_no_cycles_in_healthy_trace(self):
        """A healthy trace with no repetition should produce no findings."""
        trace = _make_trace([
            _thought_step(0, "Let me think about this"),
            _tool_step(1, "search", {"query": "test"}),
            _thought_step(2, "Now I know the answer"),
            _tool_step(3, "write", {"content": "result"}),
        ])
        findings = self.analyzer.analyze(trace)
        assert len(findings) == 0

    def test_detects_exact_repeated_subsequence(self):
        """Should detect when the same sequence of steps repeats."""
        trace = _make_trace([
            _tool_step(0, "read_file", {"path": "a.py"}),
            _tool_step(1, "write_file", {"path": "a.py", "content": "v1"}),
            _tool_step(2, "read_file", {"path": "a.py"}),
            _tool_step(3, "write_file", {"path": "a.py", "content": "v1"}),
            _tool_step(4, "read_file", {"path": "a.py"}),
            _tool_step(5, "write_file", {"path": "a.py", "content": "v1"}),
        ])
        findings = self.analyzer.analyze(trace)
        assert len(findings) > 0
        assert any(f.severity in (Severity.WARNING, Severity.ERROR) for f in findings)

    def test_short_trace_no_crash(self):
        """Should handle traces with fewer than 3 steps gracefully."""
        trace = _make_trace([_thought_step(0, "Hello")])
        findings = self.analyzer.analyze(trace)
        assert findings == []

    def test_empty_trace(self):
        """Should handle empty traces gracefully."""
        trace = _make_trace([])
        findings = self.analyzer.analyze(trace)
        assert findings == []

    def test_tool_call_graph_cycle(self):
        """Should detect cycles in the tool call transition graph."""
        trace = _make_trace([
            _tool_step(0, "read"),
            _tool_step(1, "process"),
            _tool_step(2, "read"),
            _tool_step(3, "process"),
            _tool_step(4, "read"),
            _tool_step(5, "process"),
        ])
        findings = self.analyzer.analyze(trace)
        # Should find either a subsequence repeat or a graph cycle
        assert len(findings) > 0
