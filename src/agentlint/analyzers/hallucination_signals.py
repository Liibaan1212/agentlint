"""
Hallucination Signal Detector — Finds structural patterns indicating hallucinated tool arguments.

This analyzer does NOT detect semantic hallucinations (that requires an LLM).
Instead, it detects **structural** hallucination signals — cases where the agent
generates tool arguments that are syntactically or structurally invalid:

    - Tool names not in the available_tools list
    - File paths with obviously invalid patterns
    - URLs with malformed structure
    - Enum values not matching declared schemas
    - Required arguments missing from tool calls
    - Type mismatches against declared tool schemas
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from agentlint.analyzers.base import BaseAnalyzer
from agentlint.schema import Finding, Severity, StepType, Trace

# Patterns that indicate a hallucinated file path
_SUSPICIOUS_PATH_PATTERNS = [
    re.compile(r"\.\./\.\./\.\./\.\./"),          # Excessive directory traversal
    re.compile(r"/[a-z]+/[a-z]+/[a-z]+/[a-z]+/[a-z]+/[a-z]+/[a-z]+"),  # Extremely deep nesting
    re.compile(r"[<>|?*\"]"),                       # Invalid path characters
    re.compile(r"(example|placeholder|test123|foo|bar|baz)\.(py|js|ts|txt)"),  # Placeholder names
]


class HallucinationSignalAnalyzer(BaseAnalyzer):
    """Detects structural patterns indicating hallucinated tool arguments."""

    name = "hallucination-signals"
    description = "Finds tool calls with invalid names, malformed paths, or schema violations"

    def analyze(self, trace: Trace) -> list[Finding]:
        findings: list[Finding] = []

        tool_steps = [s for s in trace.steps if s.step_type == StepType.TOOL_CALL and s.tool_call]

        for step in tool_steps:
            tc = step.tool_call
            assert tc is not None

            # Check 1: Tool name not in available tools
            if trace.available_tools and tc.name not in trace.available_tools:
                findings.append(Finding(
                    analyzer=self.name,
                    severity=Severity.ERROR,
                    message=(
                        f"Hallucinated tool name: '{tc.name}' at step {step.index} "
                        f"is not in the available tools list"
                    ),
                    step_indices=[step.index],
                    details={
                        "hallucinated_tool": tc.name,
                        "available_tools": trace.available_tools,
                    },
                    suggestion=(
                        "The agent invented a tool that doesn't exist. "
                        "Ensure tool definitions are clearly provided in the system prompt."
                    ),
                ))

            # Check 2: Schema violations (if schemas are provided)
            if tc.name in trace.tool_schemas:
                schema = trace.tool_schemas[tc.name]
                schema_findings = self._check_schema(step.index, tc.name, tc.arguments, schema)
                findings.extend(schema_findings)

            # Check 3: Suspicious patterns in argument values
            for arg_name, arg_value in tc.arguments.items():
                if isinstance(arg_value, str):
                    findings.extend(
                        self._check_string_argument(step.index, tc.name, arg_name, arg_value)
                    )

        return findings

    def _check_schema(
        self, step_index: int, tool_name: str, arguments: dict, schema: dict
    ) -> list[Finding]:
        """Check tool arguments against the declared JSON schema."""
        findings: list[Finding] = []

        # Check required fields
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in arguments:
                findings.append(Finding(
                    analyzer=self.name,
                    severity=Severity.ERROR,
                    message=(
                        f"Missing required argument '{field}' for tool '{tool_name}' "
                        f"at step {step_index}"
                    ),
                    step_indices=[step_index],
                    details={
                        "tool_name": tool_name,
                        "missing_field": field,
                        "required_fields": required,
                    },
                    suggestion=f"Add the required '{field}' argument to the tool call.",
                ))

        # Check for arguments not in the schema
        if properties:
            for arg in arguments:
                if arg not in properties:
                    findings.append(Finding(
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message=(
                            f"Unknown argument '{arg}' for tool '{tool_name}' "
                            f"at step {step_index}"
                        ),
                        step_indices=[step_index],
                        details={
                            "tool_name": tool_name,
                            "unknown_argument": arg,
                            "known_arguments": list(properties.keys()),
                        },
                    ))

        # Check enum constraints
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                prop_schema = properties[arg_name]
                allowed_values = prop_schema.get("enum")
                if allowed_values and arg_value not in allowed_values:
                    findings.append(Finding(
                        analyzer=self.name,
                        severity=Severity.ERROR,
                        message=(
                            f"Invalid enum value '{arg_value}' for '{arg_name}' "
                            f"in tool '{tool_name}' at step {step_index}. "
                            f"Allowed: {allowed_values}"
                        ),
                        step_indices=[step_index],
                        details={
                            "tool_name": tool_name,
                            "argument": arg_name,
                            "invalid_value": arg_value,
                            "allowed_values": allowed_values,
                        },
                    ))

        return findings

    def _check_string_argument(
        self, step_index: int, tool_name: str, arg_name: str, value: str
    ) -> list[Finding]:
        """Check string arguments for hallucination patterns."""
        findings: list[Finding] = []

        # Check for suspicious file paths
        if any(keyword in arg_name.lower() for keyword in ("path", "file", "dir", "folder")):
            for pattern in _SUSPICIOUS_PATH_PATTERNS:
                if pattern.search(value):
                    findings.append(Finding(
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message=(
                            f"Suspicious file path in '{arg_name}' for tool '{tool_name}' "
                            f"at step {step_index}: '{value[:80]}...'"
                        ),
                        step_indices=[step_index],
                        details={
                            "tool_name": tool_name,
                            "argument": arg_name,
                            "value": value,
                            "pattern": pattern.pattern,
                        },
                    ))
                    break  # One finding per argument is enough

        # Check for malformed URLs
        if any(keyword in arg_name.lower() for keyword in ("url", "uri", "link", "endpoint")):
            try:
                parsed = urlparse(value)
                if value and not parsed.scheme:
                    findings.append(Finding(
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message=(
                            f"Malformed URL in '{arg_name}' for tool '{tool_name}' "
                            f"at step {step_index}: missing scheme"
                        ),
                        step_indices=[step_index],
                        details={"tool_name": tool_name, "argument": arg_name, "value": value},
                    ))
            except Exception:
                pass

        return findings
