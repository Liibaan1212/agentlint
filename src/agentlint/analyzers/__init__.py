"""
AgentLint analyzers — deterministic algorithms for trajectory analysis.

Each analyzer detects a specific class of trajectory problems without
making any API calls or using any LLM. All analysis is purely algorithmic.
"""

from agentlint.analyzers.base import BaseAnalyzer
from agentlint.analyzers.context_waste import ContextWasteAnalyzer
from agentlint.analyzers.cycle_detector import CycleDetector
from agentlint.analyzers.error_cascade import ErrorCascadeAnalyzer
from agentlint.analyzers.hallucination_signals import HallucinationSignalAnalyzer
from agentlint.analyzers.progress_monitor import ProgressMonitor
from agentlint.analyzers.tool_efficiency import ToolEfficiencyAnalyzer

# Registry of all available analyzers (order matters for reporting)
ALL_ANALYZERS: list[type[BaseAnalyzer]] = [
    CycleDetector,
    ToolEfficiencyAnalyzer,
    HallucinationSignalAnalyzer,
    ProgressMonitor,
    ErrorCascadeAnalyzer,
    ContextWasteAnalyzer,
]

__all__ = [
    "ALL_ANALYZERS",
    "BaseAnalyzer",
    "ContextWasteAnalyzer",
    "CycleDetector",
    "ErrorCascadeAnalyzer",
    "HallucinationSignalAnalyzer",
    "ProgressMonitor",
    "ToolEfficiencyAnalyzer",
]
