"""
Raw JSON adapter — the universal fallback for trace ingestion.

Handles traces in AgentLint's native format or simple JSON arrays of steps.
This is the adapter used when no framework-specific format is detected.
"""

from __future__ import annotations

import uuid
from typing import Any

from agentlint.schema import Observation, Step, StepType, ToolCall, Trace


def _classify_step_type(step_data: dict[str, Any]) -> StepType:
    """Infer step type from raw JSON fields."""
    if "tool_call" in step_data or "tool_name" in step_data:
        return StepType.TOOL_CALL
    if "observation" in step_data:
        return StepType.OBSERVATION
    if "error" in step_data:
        return StepType.ERROR

    content = str(step_data.get("content", "")).lower()
    if any(kw in content for kw in ("think", "reason", "plan", "consider")):
        return StepType.THOUGHT
    if any(kw in content for kw in ("action", "execute", "run", "write")):
        return StepType.ACTION

    return StepType.UNKNOWN


def _parse_tool_call(step_data: dict[str, Any]) -> ToolCall | None:
    """Extract a ToolCall from raw step data."""
    # Handle nested tool_call object
    if "tool_call" in step_data and isinstance(step_data["tool_call"], dict):
        tc = step_data["tool_call"]
        return ToolCall(
            name=tc.get("name", tc.get("tool_name", "unknown")),
            arguments=tc.get("arguments", tc.get("args", {})),
            result=tc.get("result", tc.get("output")),
            success=tc.get("success"),
            duration_ms=tc.get("duration_ms"),
            error_message=tc.get("error_message", tc.get("error")),
        )

    # Handle flat tool fields
    if "tool_name" in step_data:
        return ToolCall(
            name=step_data["tool_name"],
            arguments=step_data.get("tool_arguments", step_data.get("arguments", {})),
            result=step_data.get("tool_result", step_data.get("result")),
            success=step_data.get("success"),
            error_message=step_data.get("error_message"),
        )

    return None


def _parse_step(index: int, step_data: dict[str, Any]) -> Step:
    """Parse a single step from raw JSON."""
    step_type = StepType(step_data["step_type"]) if "step_type" in step_data else _classify_step_type(step_data)

    content = step_data.get("content", "")
    if isinstance(content, dict):
        import json
        content = json.dumps(content)

    tool_call = _parse_tool_call(step_data)

    observation = None
    if "observation" in step_data:
        obs_data = step_data["observation"]
        if isinstance(obs_data, str):
            observation = Observation(content=obs_data)
        elif isinstance(obs_data, dict):
            observation = Observation(
                content=obs_data.get("content", str(obs_data)),
                source=obs_data.get("source"),
                token_count=obs_data.get("token_count"),
            )

    return Step(
        index=step_data.get("index", index),
        step_type=step_type,
        content=str(content),
        tool_call=tool_call,
        observation=observation,
        token_count=step_data.get("token_count", step_data.get("tokens")),
        metadata={k: v for k, v in step_data.items()
                  if k not in ("index", "step_type", "content", "tool_call", "tool_name",
                               "observation", "token_count", "tokens")},
    )


def load_raw_json(data: Any, source_path: str = "") -> Trace:
    """
    Load a trace from raw JSON data.

    Supports:
        - AgentLint native format (dict with trace_id and steps)
        - Simple list of step dicts
        - Dict with a "steps" key containing a list
    """
    steps_data: list[dict[str, Any]]
    trace_meta: dict[str, Any] = {}

    if isinstance(data, list):
        steps_data = data
    elif isinstance(data, dict):
        if "steps" in data:
            steps_data = data["steps"]
            trace_meta = {k: v for k, v in data.items() if k != "steps"}
        else:
            raise ValueError(
                "JSON object must contain a 'steps' key with a list of step objects, "
                "or be a JSON array of step objects."
            )
    else:
        raise ValueError(f"Unexpected JSON structure: expected dict or list, got {type(data)}")

    # Parse steps
    steps = [_parse_step(i, s) for i, s in enumerate(steps_data)]

    return Trace(
        trace_id=trace_meta.get("trace_id", str(uuid.uuid4())[:8]),
        agent_name=trace_meta.get("agent_name"),
        framework=trace_meta.get("framework", "raw_json"),
        task=trace_meta.get("task"),
        expected_output=trace_meta.get("expected_output"),
        steps=steps,
        available_tools=trace_meta.get("available_tools", []),
        tool_schemas=trace_meta.get("tool_schemas", {}),
        final_output=trace_meta.get("final_output"),
        success=trace_meta.get("success"),
        total_tokens=trace_meta.get("total_tokens"),
        total_duration_ms=trace_meta.get("total_duration_ms"),
        model=trace_meta.get("model"),
        metadata=trace_meta.get("metadata", {}),
    )
