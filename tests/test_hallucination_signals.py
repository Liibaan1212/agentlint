"""Tests for the hallucination signal analyzer."""

from agentlint.analyzers.hallucination_signals import HallucinationSignalAnalyzer
from agentlint.schema import Severity, Step, StepType, ToolCall, Trace


def _make_trace(steps: list[Step], **kwargs) -> Trace:
    return Trace(trace_id="test", steps=steps, **kwargs)


class TestHallucinationSignals:
    def setup_method(self):
        self.analyzer = HallucinationSignalAnalyzer()

    def test_detects_hallucinated_tool_name(self):
        """Tool name not in available_tools should be flagged."""
        trace = _make_trace(
            steps=[
                Step(
                    index=0,
                    step_type=StepType.TOOL_CALL,
                    content="Searching",
                    tool_call=ToolCall(name="magic_search", arguments={"q": "test"}),
                ),
            ],
            available_tools=["web_search", "read_file"],
        )
        findings = self.analyzer.analyze(trace)
        assert any("Hallucinated tool name" in f.message for f in findings)
        assert any(f.severity == Severity.ERROR for f in findings)

    def test_valid_tool_name_no_finding(self):
        """Tool name in available_tools should NOT be flagged."""
        trace = _make_trace(
            steps=[
                Step(
                    index=0,
                    step_type=StepType.TOOL_CALL,
                    content="Searching",
                    tool_call=ToolCall(name="web_search", arguments={"q": "test"}),
                ),
            ],
            available_tools=["web_search", "read_file"],
        )
        findings = self.analyzer.analyze(trace)
        assert not any("Hallucinated tool name" in f.message for f in findings)

    def test_detects_missing_required_argument(self):
        """Missing required arguments should be flagged."""
        trace = _make_trace(
            steps=[
                Step(
                    index=0,
                    step_type=StepType.TOOL_CALL,
                    content="Reading",
                    tool_call=ToolCall(name="read_file", arguments={}),
                ),
            ],
            available_tools=["read_file"],
            tool_schemas={
                "read_file": {
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                }
            },
        )
        findings = self.analyzer.analyze(trace)
        assert any("Missing required argument" in f.message for f in findings)

    def test_detects_suspicious_path(self):
        """Directory traversal patterns should be flagged."""
        trace = _make_trace(
            steps=[
                Step(
                    index=0,
                    step_type=StepType.TOOL_CALL,
                    content="Reading",
                    tool_call=ToolCall(
                        name="read_file",
                        arguments={"file_path": "../../../../etc/passwd"},
                    ),
                ),
            ],
        )
        findings = self.analyzer.analyze(trace)
        assert any("Suspicious file path" in f.message for f in findings)

    def test_no_tools_no_findings(self):
        """Trace with no tool calls should produce no findings."""
        trace = _make_trace(steps=[
            Step(index=0, step_type=StepType.THOUGHT, content="Thinking"),
        ])
        findings = self.analyzer.analyze(trace)
        assert len(findings) == 0

    def test_detects_invalid_enum_value(self):
        """Enum values not in schema should be flagged."""
        trace = _make_trace(
            steps=[
                Step(
                    index=0,
                    step_type=StepType.TOOL_CALL,
                    content="Setting mode",
                    tool_call=ToolCall(
                        name="set_mode",
                        arguments={"mode": "turbo_blast"},
                    ),
                ),
            ],
            available_tools=["set_mode"],
            tool_schemas={
                "set_mode": {
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["fast", "balanced", "accurate"],
                        }
                    },
                    "required": ["mode"],
                }
            },
        )
        findings = self.analyzer.analyze(trace)
        assert any("Invalid enum value" in f.message for f in findings)
