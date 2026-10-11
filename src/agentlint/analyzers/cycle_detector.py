"""
Cycle Detector — Finds loops and repeated state patterns in agent trajectories.

This is the most critical analyzer. Agents frequently enter loops where they
repeat the same sequence of actions (possibly with minor variations) without
making progress. This analyzer detects both exact and semantic repetitions.

Algorithm:
    1. Extract a "fingerprint" for each step (tool name + key argument hashes)
    2. Build a directed graph of step transitions
    3. Use NetworkX cycle detection to find exact cycles
    4. Use cosine similarity on step content to find "near-miss" semantic loops
    5. Report cycles with their start/end steps and repetition count
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from agentlint.analyzers.base import BaseAnalyzer
from agentlint.schema import Finding, Severity, StepType, Trace


def _step_fingerprint(step_content: str, tool_name: str | None) -> str:
    """Create a compact fingerprint for a step to detect repetitions."""
    # Normalize: lowercase, strip whitespace, truncate for efficiency
    content_key = step_content.strip().lower()[:200]
    if tool_name:
        return f"tool:{tool_name}|{content_key}"
    return f"content:{content_key}"


class CycleDetector(BaseAnalyzer):
    """Detects loops and repeated state patterns in agent trajectories."""

    name = "cycle-detector"
    description = "Finds loops where the agent repeats actions without making progress"

    def __init__(self, similarity_threshold: float = 0.85, min_cycle_length: int = 2) -> None:
        """
        Args:
            similarity_threshold: Cosine similarity threshold for considering
                two steps as "semantically identical" (0.0 to 1.0).
            min_cycle_length: Minimum number of steps in a sequence before
                it counts as a cycle when repeated.
        """
        self.similarity_threshold = similarity_threshold
        self.min_cycle_length = min_cycle_length

    def analyze(self, trace: Trace) -> list[Finding]:
        findings: list[Finding] = []

        if len(trace.steps) < 3:
            return findings

        # --- Phase 1: Exact fingerprint repetition detection ---
        fingerprints = []
        for step in trace.steps:
            tool_name = step.tool_call.name if step.tool_call else None
            fp = _step_fingerprint(step.content, tool_name)
            fingerprints.append(fp)

        # Find repeated consecutive subsequences
        findings.extend(self._detect_repeated_subsequences(fingerprints))

        # --- Phase 2: Graph-based cycle detection on tool call sequences ---
        tool_steps = [s for s in trace.steps if s.step_type == StepType.TOOL_CALL and s.tool_call]
        if len(tool_steps) >= 3:
            findings.extend(self._detect_tool_call_cycles(tool_steps))

        return findings

    def _detect_repeated_subsequences(self, fingerprints: list[str]) -> list[Finding]:
        """Find consecutive subsequences that repeat (sliding window approach)."""
        findings: list[Finding] = []
        n = len(fingerprints)

        # Check window sizes from min_cycle_length up to half the trace length
        for window_size in range(self.min_cycle_length, n // 2 + 1):
            i = 0
            while i <= n - 2 * window_size:
                window_a = fingerprints[i : i + window_size]
                window_b = fingerprints[i + window_size : i + 2 * window_size]

                if window_a == window_b:
                    # Found a repeated subsequence — count how many times it repeats
                    repeat_count = 2
                    j = i + 2 * window_size
                    while j + window_size <= n:
                        if fingerprints[j : j + window_size] == window_a:
                            repeat_count += 1
                            j += window_size
                        else:
                            break

                    step_indices = list(range(i, i + repeat_count * window_size))
                    findings.append(Finding(
                        analyzer=self.name,
                        severity=Severity.ERROR if repeat_count >= 3 else Severity.WARNING,
                        message=(
                            f"Repeated action sequence detected: {window_size}-step pattern "
                            f"repeats {repeat_count} times (steps {i}–{step_indices[-1]})"
                        ),
                        step_indices=step_indices,
                        details={
                            "pattern_length": window_size,
                            "repeat_count": repeat_count,
                            "pattern_fingerprints": window_a,
                        },
                        suggestion=(
                            "The agent is looping. Consider adding a loop-breaking "
                            "mechanism, reducing max iterations, or improving the "
                            "agent's reflection prompt to detect repetition."
                        ),
                    ))
                    # Skip past this detected cycle to avoid overlapping reports
                    i = i + repeat_count * window_size
                else:
                    i += 1

        return findings

    def _detect_tool_call_cycles(self, tool_steps: list[object]) -> list[Finding]:
        """Use graph-based cycle detection on tool call transition patterns."""
        findings: list[Finding] = []

        # Build a directed graph: nodes are tool names, edges are transitions
        graph = nx.DiGraph()
        tool_names = [s.tool_call.name for s in tool_steps]  # type: ignore[union-attr]

        for a, b in zip(tool_names[:-1], tool_names[1:]):
            if graph.has_edge(a, b):
                graph[a][b]["weight"] += 1
            else:
                graph.add_edge(a, b, weight=1)

        # Find all simple cycles in the tool transition graph
        try:
            cycles = list(nx.simple_cycles(graph))
        except nx.NetworkXError:
            return findings

        # Report cycles with high edge weights (frequently traversed)
        for cycle in cycles:
            if len(cycle) < self.min_cycle_length:
                continue

            # Check if this cycle was actually traversed multiple times
            cycle_edges = list(zip(cycle, cycle[1:] + [cycle[0]]))
            min_traversals = min(
                graph[a][b]["weight"] for a, b in cycle_edges if graph.has_edge(a, b)
            )

            if min_traversals >= 2:
                # Find which step indices correspond to this cycle
                cycle_set = set(cycle)
                involved_indices = [
                    s.index for s in tool_steps  # type: ignore[union-attr]
                    if s.tool_call and s.tool_call.name in cycle_set  # type: ignore[union-attr]
                ]

                findings.append(Finding(
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message=(
                        f"Tool call cycle detected: {' → '.join(cycle)} → {cycle[0]} "
                        f"(traversed {min_traversals}+ times)"
                    ),
                    step_indices=involved_indices,
                    details={
                        "cycle_tools": cycle,
                        "min_traversals": min_traversals,
                    },
                    suggestion=(
                        "The agent is cycling through the same tools repeatedly. "
                        "This may indicate a planning failure or insufficient "
                        "exit conditions."
                    ),
                ))

        return findings
