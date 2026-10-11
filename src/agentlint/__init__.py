"""
AgentLint — A deterministic linter for AI agent execution trajectories.

Like pylint for your Python code, but for AI agent behavior. Detects loops,
hallucinated tool calls, wasted context, error cascades, and inefficient paths
in milliseconds, with zero API calls, at zero cost.
"""

from agentlint.schema import Finding, Observation, Step, ToolCall, Trace
from agentlint.scoring import lint_trace

__version__ = "0.1.0"

__all__ = [
    "Finding",
    "Observation",
    "Step",
    "ToolCall",
    "Trace",
    "__version__",
    "lint_trace",
]
