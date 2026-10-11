"""
Context Waste Analyzer — Detects redundant information consuming the context budget.

Agents often re-read the same files, re-state known facts, or include duplicate
tool outputs in their reasoning. This wastes tokens and pushes important
information out of the context window.

Algorithm:
    1. Compute pairwise content similarity between observation/thought steps
    2. Flag high-similarity pairs as redundant
    3. Estimate the wasted token budget from duplicated content
"""

from __future__ import annotations

from agentlint.analyzers.base import BaseAnalyzer
from agentlint.schema import Finding, Severity, StepType, Trace


def _content_fingerprint(text: str, n: int = 4) -> set[str]:
    """Create a set of character n-grams for fast similarity comparison."""
    text = text.strip().lower()
    if len(text) < n:
        return {text}
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


class ContextWasteAnalyzer(BaseAnalyzer):
    """Detects redundant information wasting the agent's context window."""

    name = "context-waste"
    description = "Finds duplicate or redundant content consuming token budget"

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        min_content_length: int = 50,
    ) -> None:
        """
        Args:
            similarity_threshold: Jaccard similarity above which two pieces
                of content are considered duplicates.
            min_content_length: Minimum character length for content to be
                worth comparing (skip trivial snippets).
        """
        self.similarity_threshold = similarity_threshold
        self.min_content_length = min_content_length

    def analyze(self, trace: Trace) -> list[Finding]:
        findings: list[Finding] = []

        # Collect steps with substantial content
        content_steps = [
            s for s in trace.steps
            if len(s.content) >= self.min_content_length
            and s.step_type in (StepType.OBSERVATION, StepType.THOUGHT, StepType.TOOL_CALL)
        ]

        if len(content_steps) < 2:
            return findings

        # Compute fingerprints once
        fingerprints = {s.index: _content_fingerprint(s.content) for s in content_steps}

        # Find duplicate pairs (compare each step with all later steps)
        duplicate_pairs: list[tuple[int, int, float]] = []
        reported_indices: set[int] = set()

        for i, step_a in enumerate(content_steps):
            for step_b in content_steps[i + 1 :]:
                sim = _jaccard_similarity(
                    fingerprints[step_a.index],
                    fingerprints[step_b.index],
                )
                if sim >= self.similarity_threshold:
                    duplicate_pairs.append((step_a.index, step_b.index, sim))
                    reported_indices.add(step_b.index)  # The later occurrence is "waste"

        if not duplicate_pairs:
            return findings

        # Report individual duplicate pairs (up to a reasonable limit)
        for idx_a, idx_b, sim in duplicate_pairs[:10]:
            findings.append(Finding(
                analyzer=self.name,
                severity=Severity.INFO,
                message=(
                    f"Redundant content: step {idx_b} is {sim:.0%} similar "
                    f"to step {idx_a}"
                ),
                step_indices=[idx_a, idx_b],
                details={
                    "similarity": round(sim, 3),
                    "original_step": idx_a,
                    "duplicate_step": idx_b,
                },
            ))

        # Report overall context waste
        if len(reported_indices) >= 3:
            waste_ratio = len(reported_indices) / len(content_steps)
            findings.append(Finding(
                analyzer=self.name,
                severity=Severity.WARNING if waste_ratio > 0.3 else Severity.INFO,
                message=(
                    f"Context waste: {len(reported_indices)} out of {len(content_steps)} "
                    f"content steps contain redundant information ({waste_ratio:.0%} waste)"
                ),
                step_indices=sorted(reported_indices),
                details={
                    "wasted_steps": len(reported_indices),
                    "total_content_steps": len(content_steps),
                    "waste_ratio": round(waste_ratio, 3),
                },
                suggestion=(
                    "The agent is repeating information it already has. "
                    "Consider implementing context compression or deduplication "
                    "in the agent's memory management."
                ),
            ))

        return findings
