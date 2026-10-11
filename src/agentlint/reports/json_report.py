"""
JSON report — machine-readable output for CI/CD integration.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentlint.scoring import LintResult


def generate_json_report(result: LintResult) -> str:
    """Generate a JSON string report from a LintResult."""
    return result.model_dump_json(indent=2)
