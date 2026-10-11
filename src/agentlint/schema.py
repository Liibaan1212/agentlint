"""
Universal trace schema for AgentLint.

This module defines the canonical data model that all agent execution traces
are normalized into, regardless of which framework produced them. Every
framework adapter in `agentlint.ingest` converts framework-specific logs
into these Pydantic models before any analysis occurs.

Design principles:
    - Framework-agnostic: captures the universal structure of agent execution
    - Minimal required fields: adapters can omit what they don't have
    - Rich optional metadata: analyzers use what's available
    - Immutable after creation: traces are read-only data for analysis
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level for findings reported by analyzers."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class StepType(str, Enum):
    """Classification of what happened during an agent step."""

    THOUGHT = "thought"          # Internal reasoning / chain-of-thought
    TOOL_CALL = "tool_call"      # Agent invoked a tool
    OBSERVATION = "observation"  # Result returned from a tool or environment
    ACTION = "action"            # Agent took a non-tool action (e.g., wrote output)
    ERROR = "error"              # An error occurred during this step
    HUMAN_INPUT = "human_input"  # Human-in-the-loop intervention
    UNKNOWN = "unknown"          # Could not classify


class ToolCall(BaseModel):
    """A single tool invocation by the agent."""

    name: str = Field(description="Name of the tool that was called")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the tool",
    )
    result: Any | None = Field(
        default=None,
        description="Return value from the tool, if available",
    )
    success: bool | None = Field(
        default=None,
        description="Whether the tool call succeeded",
    )
    duration_ms: float | None = Field(
        default=None,
        description="Wall-clock execution time in milliseconds",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the tool call failed",
    )


class Observation(BaseModel):
    """An observation received by the agent from the environment."""

    content: str = Field(description="The observation content")
    source: str | None = Field(
        default=None,
        description="Where the observation came from (e.g., tool name, user, system)",
    )
    token_count: int | None = Field(
        default=None,
        description="Number of tokens in this observation, if known",
    )


class Step(BaseModel):
    """
    A single step in an agent's execution trajectory.

    A step represents one discrete action or event: a thought, a tool call,
    an observation, an error, etc. The sequence of steps forms the trajectory
    that AgentLint analyzes.
    """

    index: int = Field(description="0-based position of this step in the trajectory")
    step_type: StepType = Field(description="What kind of step this is")
    content: str = Field(
        default="",
        description="Text content of this step (thought text, action description, etc.)",
    )
    tool_call: ToolCall | None = Field(
        default=None,
        description="Tool call details, if this step is a tool invocation",
    )
    observation: Observation | None = Field(
        default=None,
        description="Observation details, if this step is an observation",
    )
    timestamp: datetime | None = Field(
        default=None,
        description="When this step occurred",
    )
    token_count: int | None = Field(
        default=None,
        description="Tokens consumed by this step, if known",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary framework-specific metadata",
    )


class Trace(BaseModel):
    """
    A complete agent execution trajectory.

    This is the top-level object that AgentLint analyzes. It contains the
    ordered sequence of steps the agent took, plus metadata about the task,
    the agent, and the tools available.
    """

    # Identity
    trace_id: str = Field(description="Unique identifier for this trace")
    agent_name: str | None = Field(
        default=None,
        description="Name or type of the agent that produced this trace",
    )
    framework: str | None = Field(
        default=None,
        description="Framework that produced this trace (e.g., 'langgraph', 'crewai')",
    )

    # Task definition
    task: str | None = Field(
        default=None,
        description="The goal or prompt the agent was given",
    )
    expected_output: str | None = Field(
        default=None,
        description="Expected result, if known (for evaluation)",
    )

    # The trajectory itself
    steps: list[Step] = Field(
        default_factory=list,
        description="Ordered sequence of execution steps",
    )

    # Tool schema information (used by hallucination detector)
    available_tools: list[str] = Field(
        default_factory=list,
        description="Names of tools the agent was allowed to use",
    )
    tool_schemas: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="JSON schemas for tool arguments, keyed by tool name",
    )

    # Outcome
    final_output: str | None = Field(
        default=None,
        description="The agent's final response or output",
    )
    success: bool | None = Field(
        default=None,
        description="Whether the task was completed successfully, if known",
    )

    # Metadata
    total_tokens: int | None = Field(
        default=None,
        description="Total tokens consumed across the entire trajectory",
    )
    total_duration_ms: float | None = Field(
        default=None,
        description="Total wall-clock time in milliseconds",
    )
    model: str | None = Field(
        default=None,
        description="LLM model used (e.g., 'gpt-4o', 'claude-3.5-sonnet')",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional metadata",
    )

    @property
    def num_steps(self) -> int:
        """Total number of steps in the trajectory."""
        return len(self.steps)

    @property
    def tool_calls(self) -> list[Step]:
        """All steps that are tool invocations."""
        return [s for s in self.steps if s.step_type == StepType.TOOL_CALL]

    @property
    def errors(self) -> list[Step]:
        """All steps that are errors."""
        return [s for s in self.steps if s.step_type == StepType.ERROR]


class Finding(BaseModel):
    """
    A single issue detected by an AgentLint analyzer.

    Findings are the core output of the analysis engine. Each finding
    points to specific steps in the trajectory and explains what was
    detected and why it matters.
    """

    analyzer: str = Field(description="Name of the analyzer that produced this finding")
    severity: Severity = Field(description="How severe this issue is")
    message: str = Field(description="Human-readable description of the issue")
    step_indices: list[int] = Field(
        default_factory=list,
        description="Which steps (0-based) are involved in this finding",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured details specific to the analyzer",
    )
    suggestion: str | None = Field(
        default=None,
        description="Actionable suggestion for fixing the issue",
    )
