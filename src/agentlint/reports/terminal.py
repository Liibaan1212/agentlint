"""
Terminal report — Rich-formatted output for the CLI.

Produces a clean, colored terminal output showing the overall score,
per-analyzer breakdown, and individual findings with step references.
"""

from __future__ import annotations

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentlint.schema import Severity

# Import at function level to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentlint.scoring import LintResult

# Use ASCII-safe indicators if console is not utf-8
_IS_UTF8 = getattr(sys.stdout, "encoding", "").lower() in ("utf-8", "utf8")

_SEVERITY_STYLES = {
    Severity.ERROR: ("[ERROR]" if not _IS_UTF8 else "❌", "bold red"),
    Severity.WARNING: ("[WARN]" if not _IS_UTF8 else "⚠️ ", "yellow"),
    Severity.INFO: ("[INFO]" if not _IS_UTF8 else "ℹ️ ", "dim"),
}


def print_terminal_report(result: LintResult, verbose: bool = False) -> None:
    """Print a formatted lint report to the terminal."""
    console = Console(legacy_windows=False if _IS_UTF8 else None)

    # Header with overall score
    score = result.score
    if score >= 0.8:
        score_color = "green"
        score_indicator = "[PASS]" if not _IS_UTF8 else "✅"
    elif score >= 0.5:
        score_color = "yellow"
        score_indicator = "[WARN]" if not _IS_UTF8 else "⚠️"
    else:
        score_color = "red"
        score_indicator = "[FAIL]" if not _IS_UTF8 else "❌"

    header = Text()
    header.append(f"\n{score_indicator} AgentLint Score: ", style="bold")
    header.append(f"{score:.1%}", style=f"bold {score_color}")
    header.append(f"  ({result.num_steps} steps, {result.analysis_time_ms:.1f}ms)")
    console.print(header)

    # Summary counts
    summary = Text()
    if result.error_count:
        summary.append(f"  {result.error_count} error(s)", style="red")
    if result.warning_count:
        if summary:
            summary.append("  ")
        summary.append(f"  {result.warning_count} warning(s)", style="yellow")
    if result.info_count:
        if summary:
            summary.append("  ")
        summary.append(f"  {result.info_count} info", style="dim")
    if not result.findings:
        summary.append("  No issues found!", style="green")
    console.print(summary)

    # Per-analyzer scores table
    if result.analyzer_scores:
        table = Table(title="\nAnalyzer Breakdown", show_header=True, header_style="bold")
        table.add_column("Analyzer", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Status", justify="center")

        for name, score_val in sorted(result.analyzer_scores.items()):
            if score_val >= 0.8:
                style = "green"
                status = "PASS" if not _IS_UTF8 else "✅"
            elif score_val >= 0.5:
                style = "yellow"
                status = "WARN" if not _IS_UTF8 else "⚠️"
            else:
                style = "red"
                status = "FAIL" if not _IS_UTF8 else "❌"
            table.add_row(name, f"[{style}]{score_val:.1%}[/{style}]", status)

        console.print(table)

    # Individual findings
    if result.findings:
        console.print("\n[bold]Findings:[/bold]\n")

        for finding in result.findings:
            emoji, style = _SEVERITY_STYLES.get(finding.severity, ("?", ""))

            msg = finding.message
            if not _IS_UTF8:
                msg = msg.replace("–", "-").replace("—", "-").replace("→", "->")

            console.print(f"  {emoji} [{style}]{finding.severity.value.upper()}[/{style}]", end=" ")
            console.print(f"[bold]{finding.analyzer}[/bold]: {msg}")

            if finding.step_indices:
                steps_str = ", ".join(str(i) for i in finding.step_indices[:10])
                if len(finding.step_indices) > 10:
                    steps_str += f" ... (+{len(finding.step_indices) - 10} more)"
                console.print(f"       Steps: {steps_str}", style="dim")

            if verbose and finding.suggestion:
                sug_prefix = "Suggestion: " if not _IS_UTF8 else "💡 "
                console.print(f"       {sug_prefix}{finding.suggestion}", style="italic dim")

            if verbose and finding.details:
                for key, value in finding.details.items():
                    if not isinstance(value, (list, dict)) or len(str(value)) < 80:
                        console.print(f"       {key}: {value}", style="dim")

            console.print()

    # Final verdict
    console.print()
    if result.passed:
        console.print(Panel("[green]PASSED[/green]", title="Result", border_style="green"))
    else:
        console.print(Panel("[red]FAILED[/red]", title="Result", border_style="red"))
