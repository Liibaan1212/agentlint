"""
Progress Monitor — Measures whether the agent is making forward progress.

The core idea: in a healthy trajectory, intermediate outputs should get
progressively closer to the final output. If the agent oscillates, plateaus,
or regresses, something is wrong.

Algorithm:
    1. For each step that has content, compute a "distance to final output"
       using character-level edit distance (normalized Levenshtein)
    2. Plot a "progress curve" — distance should decrease over time
    3. Score the trajectory based on how monotonically the curve decreases
    4. Flag steps where progress reverses significantly
"""

from __future__ import annotations

from agentlint.analyzers.base import BaseAnalyzer
from agentlint.schema import Finding, Severity, StepType, Trace


def _normalized_edit_similarity(a: str, b: str) -> float:
    """
    Compute normalized similarity between two strings (0.0 = identical, 1.0 = completely different).

    Uses a simplified character-level comparison for speed. Not a full Levenshtein
    calculation (which is O(n*m)), but a fast approximation based on character overlap.
    """
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0

    # Truncate for performance
    a = a[:500]
    b = b[:500]

    # Character n-gram overlap (fast approximation of edit similarity)
    n = 3
    if len(a) < n or len(b) < n:
        # Fall back to character set overlap for very short strings
        set_a = set(a.lower())
        set_b = set(b.lower())
        if not set_a or not set_b:
            return 1.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return 1.0 - (intersection / union)

    ngrams_a = {a[i : i + n] for i in range(len(a) - n + 1)}
    ngrams_b = {b[i : i + n] for i in range(len(b) - n + 1)}

    if not ngrams_a or not ngrams_b:
        return 1.0

    intersection = len(ngrams_a & ngrams_b)
    union = len(ngrams_a | ngrams_b)
    return 1.0 - (intersection / union)


class ProgressMonitor(BaseAnalyzer):
    """Measures whether the agent is making forward progress toward its goal."""

    name = "progress-monitor"
    description = "Detects stalled, oscillating, or regressing trajectory progress"

    def __init__(
        self,
        regression_threshold: float = 0.15,
        plateau_steps: int = 5,
    ) -> None:
        """
        Args:
            regression_threshold: Minimum increase in distance-to-goal
                that counts as a regression.
            plateau_steps: Number of consecutive steps with no progress
                before flagging a plateau.
        """
        self.regression_threshold = regression_threshold
        self.plateau_steps = plateau_steps

    def analyze(self, trace: Trace) -> list[Finding]:
        findings: list[Finding] = []

        # We need a final output to measure progress against
        if not trace.final_output or len(trace.steps) < 3:
            return findings

        # Collect steps that have meaningful content
        content_steps = [
            s for s in trace.steps
            if s.content and s.step_type in (StepType.THOUGHT, StepType.ACTION, StepType.TOOL_CALL)
        ]

        if len(content_steps) < 3:
            return findings

        # Compute progress curve: distance to final output at each step
        final = trace.final_output
        distances = []
        for step in content_steps:
            dist = _normalized_edit_similarity(step.content, final)
            distances.append((step.index, dist))

        # Detect regressions: points where distance increases significantly
        regressions = []
        for i in range(1, len(distances)):
            prev_idx, prev_dist = distances[i - 1]
            curr_idx, curr_dist = distances[i]
            if curr_dist - prev_dist > self.regression_threshold:
                regressions.append(curr_idx)

        if len(regressions) > len(distances) // 3:
            findings.append(Finding(
                analyzer=self.name,
                severity=Severity.WARNING,
                message=(
                    f"Frequent progress regressions: {len(regressions)} steps moved "
                    f"further from the goal (out of {len(distances)} content steps)"
                ),
                step_indices=regressions,
                details={
                    "regression_count": len(regressions),
                    "total_content_steps": len(distances),
                    "regression_ratio": round(len(regressions) / len(distances), 3),
                },
                suggestion=(
                    "The agent's intermediate outputs are not converging toward "
                    "the final answer. Consider improving planning or adding "
                    "self-reflection checkpoints."
                ),
            ))

        # Detect plateaus: many consecutive steps with no meaningful change
        plateau_start = None
        for i in range(1, len(distances)):
            _, prev_dist = distances[i - 1]
            step_idx, curr_dist = distances[i]
            if abs(curr_dist - prev_dist) < 0.02:  # Minimal change
                if plateau_start is None:
                    plateau_start = i - 1
            else:
                if plateau_start is not None:
                    plateau_length = i - plateau_start
                    if plateau_length >= self.plateau_steps:
                        plateau_indices = [distances[j][0] for j in range(plateau_start, i)]
                        findings.append(Finding(
                            analyzer=self.name,
                            severity=Severity.WARNING,
                            message=(
                                f"Progress plateau: {plateau_length} consecutive steps "
                                f"with no meaningful progress (steps "
                                f"{plateau_indices[0]}–{plateau_indices[-1]})"
                            ),
                            step_indices=plateau_indices,
                            details={
                                "plateau_length": plateau_length,
                                "plateau_start": plateau_indices[0],
                                "plateau_end": plateau_indices[-1],
                            },
                            suggestion=(
                                "The agent spent multiple steps without making progress. "
                                "Consider adding early termination or strategy-switching logic."
                            ),
                        ))
                    plateau_start = None

        return findings
