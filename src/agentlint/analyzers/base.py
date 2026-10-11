"""
Base analyzer interface for AgentLint.

Every analyzer must inherit from BaseAnalyzer and implement the `analyze`
method. Analyzers MUST be:
    - Deterministic: same input always produces same output
    - Zero-cost: no API calls, no network, no LLM
    - Fast: < 100ms for a 50-step trace
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentlint.schema import Finding, Trace


class BaseAnalyzer(ABC):
    """
    Abstract base class for all AgentLint analyzers.

    Subclasses must define:
        name: A short, kebab-case identifier (e.g., "cycle-detector")
        description: A one-line summary of what this analyzer detects

    Subclasses must implement:
        analyze(trace) -> list[Finding]: The core analysis logic
    """

    name: str = "base"
    description: str = "Base analyzer (not directly usable)"

    @abstractmethod
    def analyze(self, trace: Trace) -> list[Finding]:
        """
        Analyze a trace and return a list of findings.

        Args:
            trace: The normalized agent execution trace to analyze.

        Returns:
            A list of Finding objects, each describing a detected issue.
            Return an empty list if no issues are found.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
