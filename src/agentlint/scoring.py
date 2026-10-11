"""
Aggregate scoring engine for AgentLint.

Runs all registered analyzers against a trace and produces an overall
trajectory quality score (0.0 to 1.0) plus the combined list of findings.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentlint.analyzers import ALL_ANALYZERS, BaseAnalyzer
from agentlint.ingest import load_trace
from agentlint.schema import Finding, Severity, Trace


class LintResult(BaseModel):
    """Complete result from linting an agent trajectory."""

    # Overall score (1.0 = perfect, 0.0 = terrible)
    score: float = Field(description="Overall trajectory quality score (0.0 to 1.0)")

    # All findings from all analyzers
    findings: list[Finding] = Field(default_factory=list)

    # Per-analyzer breakdown
    analyzer_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Individual score from each analyzer (1.0 = no issues found)",
    )

    # Metadata
    trace_id: str = Field(default="")
    num_steps: int = Field(default=0)
    analysis_time_ms: float = Field(default=0.0)

    @property
    def passed(self) -> bool:
        """Whether the trajectory passed linting (no errors)."""
        return not any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)


def _compute_analyzer_score(findings: list[Finding]) -> float:
    """
    Convert a list of findings into a score between 0.0 and 1.0.

    Scoring:
        - Start at 1.0
        - Each ERROR deducts 0.2
        - Each WARNING deducts 0.1
        - Each INFO deducts 0.02
        - Floor at 0.0
    """
    score = 1.0
    for finding in findings:
        if finding.severity == Severity.ERROR:
            score -= 0.2
        elif finding.severity == Severity.WARNING:
            score -= 0.1
        elif finding.severity == Severity.INFO:
            score -= 0.02
    return max(0.0, round(score, 3))


def lint_trace(
    source: str | Path | Trace,
    analyzers: list[BaseAnalyzer] | None = None,
) -> LintResult:
    """
    Lint an agent execution trace and return a scored result.

    This is the main entry point for the AgentLint Python API.

    Args:
        source: Either a file path to a trace JSON file, or a Trace object.
        analyzers: Optional list of analyzer instances. If None, all default
            analyzers are used.

    Returns:
        A LintResult containing the overall score, all findings, and metadata.

    Example:
        >>> result = lint_trace("my_agent_trace.json")
        >>> print(result.score)
        0.85
        >>> assert result.score > 0.7
    """
    # Load the trace
    if isinstance(source, Trace):
        trace = source
    else:
        trace = load_trace(source)

    # Instantiate default analyzers if none provided
    if analyzers is None:
        analyzers = [cls() for cls in ALL_ANALYZERS]

    # Run all analyzers and collect findings
    all_findings: list[Finding] = []
    analyzer_scores: dict[str, float] = {}

    start_time = time.perf_counter()

    for analyzer in analyzers:
        analyzer_findings = analyzer.analyze(trace)
        all_findings.extend(analyzer_findings)
        analyzer_scores[analyzer.name] = _compute_analyzer_score(analyzer_findings)

    analysis_time_ms = (time.perf_counter() - start_time) * 1000

    # Compute overall score (weighted average of analyzer scores)
    if analyzer_scores:
        overall_score = sum(analyzer_scores.values()) / len(analyzer_scores)
    else:
        overall_score = 1.0

    return LintResult(
        score=round(overall_score, 3),
        findings=all_findings,
        analyzer_scores=analyzer_scores,
        trace_id=trace.trace_id,
        num_steps=trace.num_steps,
        analysis_time_ms=round(analysis_time_ms, 2),
    )
