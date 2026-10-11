"""
LangGraph trace adapter — converts LangGraph checkpoint/trace exports.

This is a placeholder that will be fully implemented when we have access
to real LangGraph trace exports. The schema detection is already wired
into the ingest layer.
"""

from __future__ import annotations

from typing import Any

from agentlint.schema import Trace


def load_langgraph_trace(data: dict[str, Any]) -> Trace:
    """
    Convert a LangGraph trace export into an AgentLint Trace.

    TODO: Implement once we have real LangGraph trace samples.
    Currently falls back to raw JSON parsing.
    """
    from agentlint.ingest.raw_json import load_raw_json
    return load_raw_json(data)
