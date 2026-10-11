"""OpenTelemetry trace adapter — converts OTLP trace exports."""

from __future__ import annotations

from typing import Any

from agentlint.schema import Trace


def load_otel_trace(data: dict[str, Any]) -> Trace:
    """Convert an OpenTelemetry OTLP trace export into an AgentLint Trace."""
    from agentlint.ingest.raw_json import load_raw_json
    return load_raw_json(data)
