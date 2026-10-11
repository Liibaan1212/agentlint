"""
AgentLint CLI — the command-line interface.

Usage:
    agentlint check trace.json              # Lint a trace file
    agentlint check trace.json --verbose    # Detailed per-step annotations
    agentlint check trace.json --format json # Machine-readable output
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from agentlint.reports.terminal import print_terminal_report
from agentlint.scoring import lint_trace

app = typer.Typer(
    name="agentlint",
    help="🔍 A deterministic linter for AI agent execution trajectories.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def check(
    trace_file: Path = typer.Argument(
        ...,
        help="Path to the agent trace JSON file to lint.",
        exists=True,
        readable=True,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show detailed per-step annotations.",
    ),
    output_format: str = typer.Option(
        "terminal", "--format", "-f",
        help="Output format: 'terminal' (default), 'json'.",
    ),
    fail_under: float = typer.Option(
        0.0, "--fail-under",
        help="Exit with code 1 if score is below this threshold (0.0 to 1.0).",
    ),
) -> None:
    """Lint an agent execution trace and report findings."""
    try:
        result = lint_trace(trace_file)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {trace_file}")
        raise typer.Exit(code=2)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=2)

    if output_format == "json":
        console.print(result.model_dump_json(indent=2))
    else:
        print_terminal_report(result, verbose=verbose)

    # Exit with error code if score is below threshold
    if result.score < fail_under:
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print the AgentLint version."""
    from agentlint import __version__
    console.print(f"agentlint {__version__}")


if __name__ == "__main__":
    app()
