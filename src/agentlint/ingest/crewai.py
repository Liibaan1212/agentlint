"""CrewAI trace adapter — placeholder for CrewAI output format conversion."""

from __future__ import annotations

from typing import Any

from agentlint.schema import Trace


def load_crewai_trace(data: dict[str, Any]) -> Trace:
    """Convert a CrewAI execution output into an AgentLint Trace."""
    from agentlint.ingest.raw_json import load_raw_json
    return load_raw_json(data)
