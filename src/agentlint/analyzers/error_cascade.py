"""
Error Cascade Analyzer — Traces how early errors propagate through subsequent steps.

When step N fails, the agent often continues operating on corrupted state.
This analyzer identifies error origins and traces which subsequent steps
were likely affected by each error.

Algorithm:
    1. Identify all error steps (step_type == ERROR or tool_call.success == False)
    2. For each error, examine subsequent steps for "contamination signals":
       - References to the failed tool's output
       - Attempts to use results that don't exist
       - Repeated retries of the same failed operation
    3. Build a causal chain from error origin to affected steps
    4. Report the cascade depth and impact
"""

from __future__ import annotations

from agentlint.analyzers.base import BaseAnalyzer
from agentlint.schema import Finding, Severity, Step, StepType, Trace


class ErrorCascadeAnalyzer(BaseAnalyzer):
    """Traces how early errors propagate and corrupt downstream steps."""

    name = "error-cascade"
    description = "Detects error chains where one failure corrupts subsequent steps"

    def __init__(self, max_cascade_depth: int = 10) -> None:
        """
        Args:
            max_cascade_depth: Maximum number of steps after an error to
                check for contamination.
        """
        self.max_cascade_depth = max_cascade_depth

    def analyze(self, trace: Trace) -> list[Finding]:
        findings: list[Finding] = []

        if len(trace.steps) < 2:
            return findings

        # Find all error steps
        error_steps: list[Step] = []
        for step in trace.steps:
            is_error = step.step_type == StepType.ERROR
            is_failed_tool = (
                step.step_type == StepType.TOOL_CALL
                and step.tool_call is not None
                and step.tool_call.success is False
            )
            if is_error or is_failed_tool:
                error_steps.append(step)

        if not error_steps:
            return findings

        # For each error, trace its downstream impact
        for error_step in error_steps:
            cascade_indices = [error_step.index]
            error_tool_name = (
                error_step.tool_call.name if error_step.tool_call else None
            )
            error_message = (
                error_step.tool_call.error_message
                if error_step.tool_call and error_step.tool_call.error_message
                else error_step.content
            )

            # Look at subsequent steps for contamination signals
            for subsequent in trace.steps[error_step.index + 1 :]:
                if len(cascade_indices) > self.max_cascade_depth:
                    break

                is_contaminated = False

                # Signal 1: Retry of the same failed tool with same/similar args
                if (
                    subsequent.step_type == StepType.TOOL_CALL
                    and subsequent.tool_call
                    and error_tool_name
                    and subsequent.tool_call.name == error_tool_name
                ):
                    is_contaminated = True

                # Signal 2: Subsequent step references the error message
                if error_message and error_message[:50] in subsequent.content:
                    is_contaminated = True

                # Signal 3: Subsequent step also fails
                if (
                    subsequent.step_type == StepType.ERROR
                    or (subsequent.tool_call and subsequent.tool_call.success is False)
                ):
                    is_contaminated = True

                if is_contaminated:
                    cascade_indices.append(subsequent.index)

            # Report if the cascade is significant (more than just the original error)
            if len(cascade_indices) >= 3:
                findings.append(Finding(
                    analyzer=self.name,
                    severity=Severity.ERROR if len(cascade_indices) >= 5 else Severity.WARNING,
                    message=(
                        f"Error cascade: failure at step {error_step.index} "
                        f"propagated through {len(cascade_indices) - 1} subsequent steps "
                        f"(steps {cascade_indices[0]}–{cascade_indices[-1]})"
                    ),
                    step_indices=cascade_indices,
                    details={
                        "origin_step": error_step.index,
                        "cascade_depth": len(cascade_indices) - 1,
                        "origin_tool": error_tool_name,
                        "origin_error": error_message[:200] if error_message else None,
                    },
                    suggestion=(
                        "The agent failed to recover from an error and continued "
                        "operating on corrupted state. Consider adding error-recovery "
                        "logic or a 'start fresh' fallback after critical failures."
                    ),
                ))

        return findings
