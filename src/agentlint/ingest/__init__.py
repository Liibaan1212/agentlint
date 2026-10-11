"""
Trace ingestion — loads and normalizes agent traces from various sources.

Every framework produces logs in a different format. The ingest layer
converts them all into AgentLint's universal Trace schema.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentlint.ingest.raw_json import load_raw_json
from agentlint.schema import Trace


def load_trace(source: str | Path) -> Trace:
    """
    Load an agent trace from a file path.

    Automatically detects the trace format and applies the appropriate adapter.

    Args:
        source: Path to a JSON trace file.

    Returns:
        A normalized Trace object ready for analysis.

    Raises:
        FileNotFoundError: If the trace file does not exist.
        ValueError: If the trace format cannot be determined or parsed.
    """
    path = Path(source)

    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")

    if not path.suffix.lower() == ".json":
        raise ValueError(f"Unsupported file type: {path.suffix}. Only .json is supported.")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Auto-detect format based on structure
    if isinstance(data, dict):
        # Check for AgentLint native format
        if "trace_id" in data and "steps" in data:
            return Trace.model_validate(data)

        # Check for LangGraph format
        if "channel_values" in data or "configurable" in data:
            from agentlint.ingest.langgraph import load_langgraph_trace
            return load_langgraph_trace(data)

        # Check for CrewAI format
        if "crew_output" in data or "tasks_output" in data:
            from agentlint.ingest.crewai import load_crewai_trace
            return load_crewai_trace(data)

        # Check for OpenTelemetry format
        if "resourceSpans" in data:
            from agentlint.ingest.opentelemetry import load_otel_trace
            return load_otel_trace(data)

    # Fall back to raw JSON adapter
    return load_raw_json(data, source_path=str(path))


__all__ = ["load_trace"]
