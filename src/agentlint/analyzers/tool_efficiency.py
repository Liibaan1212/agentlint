"""
Tool Efficiency Analyzer — Measures the ratio of productive to wasteful tool calls.

A "productive" tool call is one that:
    - Returned new information not already present in previous observations
    - Changed state in a meaningful way (success=True with non-empty result)
    - Was not an exact duplicate of a previous call with the same arguments

A "wasteful" tool call is one that:
    - Duplicates a previous call with identical arguments
    - Returned an error that was already encountered
    - Produced no result and no state change

The efficiency ratio (0.0 to 1.0) is:
    productive_calls / total_tool_calls
"""

from __future__ import annotations

import json
from hashlib import sha256

from agentlint.analyzers.base import BaseAnalyzer
from agentlint.schema import Finding, Severity, StepType, Trace


def _call_signature(name: str, arguments: dict) -> str:
    """Create a deterministic hash of a tool call for deduplication."""
    canonical = json.dumps({"name": name, "args": arguments}, sort_keys=True, default=str)
    return sha256(canonical.encode()).hexdigest()[:16]


class ToolEfficiencyAnalyzer(BaseAnalyzer):
    """Measures the ratio of productive to wasteful tool calls."""

    name = "tool-efficiency"
    description = "Detects redundant, duplicate, or no-op tool invocations"

    def __init__(self, warning_threshold: float = 0.5, error_threshold: float = 0.3) -> None:
        """
        Args:
            warning_threshold: Efficiency below this triggers a warning.
            error_threshold: Efficiency below this triggers an error.
        """
        self.warning_threshold = warning_threshold
        self.error_threshold = error_threshold

    def analyze(self, trace: Trace) -> list[Finding]:
        findings: list[Finding] = []

        tool_steps = [s for s in trace.steps if s.step_type == StepType.TOOL_CALL and s.tool_call]

        if not tool_steps:
            return findings

        # Track seen call signatures for duplicate detection
        seen_signatures: dict[str, int] = {}  # signature -> first step index
        duplicate_indices: list[int] = []
        failed_retry_indices: list[int] = []
        noop_indices: list[int] = []

        for step in tool_steps:
            tc = step.tool_call
            assert tc is not None  # guaranteed by filter above

            sig = _call_signature(tc.name, tc.arguments)

            # Check for exact duplicate calls
            if sig in seen_signatures:
                duplicate_indices.append(step.index)
                findings.append(Finding(
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message=(
                        f"Duplicate tool call: '{tc.name}' at step {step.index} "
                        f"has identical arguments to step {seen_signatures[sig]}"
                    ),
                    step_indices=[seen_signatures[sig], step.index],
                    details={
                        "tool_name": tc.name,
                        "original_step": seen_signatures[sig],
                        "duplicate_step": step.index,
                    },
                    suggestion=(
                        "Cache the result of the first call instead of repeating it. "
                        "If retrying after an error, vary the approach."
                    ),
                ))
            else:
                seen_signatures[sig] = step.index

            # Check for failed calls that produce no useful result
            if tc.success is False and tc.error_message:
                failed_retry_indices.append(step.index)

            # Check for no-op calls (success but empty result)
            if tc.success is True and tc.result in (None, "", {}, []):
                noop_indices.append(step.index)

        # Calculate overall efficiency
        total = len(tool_steps)
        wasteful = len(set(duplicate_indices) | set(noop_indices))
        productive = total - wasteful
        efficiency = productive / total if total > 0 else 1.0

        # Report overall efficiency
        if efficiency < self.error_threshold:
            findings.append(Finding(
                analyzer=self.name,
                severity=Severity.ERROR,
                message=(
                    f"Very low tool efficiency: {efficiency:.0%} "
                    f"({productive}/{total} productive calls)"
                ),
                step_indices=duplicate_indices + noop_indices,
                details={
                    "efficiency": round(efficiency, 3),
                    "total_calls": total,
                    "productive_calls": productive,
                    "duplicate_calls": len(duplicate_indices),
                    "noop_calls": len(noop_indices),
                    "failed_calls": len(failed_retry_indices),
                },
                suggestion=(
                    "The agent is making many redundant or empty tool calls. "
                    "Consider improving tool selection logic or adding result caching."
                ),
            ))
        elif efficiency < self.warning_threshold:
            findings.append(Finding(
                analyzer=self.name,
                severity=Severity.WARNING,
                message=(
                    f"Low tool efficiency: {efficiency:.0%} "
                    f"({productive}/{total} productive calls)"
                ),
                step_indices=duplicate_indices + noop_indices,
                details={
                    "efficiency": round(efficiency, 3),
                    "total_calls": total,
                    "productive_calls": productive,
                    "duplicate_calls": len(duplicate_indices),
                    "noop_calls": len(noop_indices),
                },
            ))

        return findings
