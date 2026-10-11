# Contributing to AgentLint

Thank you for your interest in contributing to AgentLint! This document explains how to get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Liibaan1212/agentlint.git
cd agentlint

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/
```

## How to Contribute

### Adding a New Analyzer

Analyzers are the core of AgentLint. Each analyzer detects a specific class of trajectory problems.

1. Create a new file in `src/agentlint/analyzers/`
2. Implement the `BaseAnalyzer` interface:

```python
from agentlint.analyzers.base import BaseAnalyzer, Finding
from agentlint.schema import Trace

class MyAnalyzer(BaseAnalyzer):
    """One-line description of what this analyzer detects."""

    name = "my-analyzer"
    description = "Detects X patterns in agent trajectories"

    def analyze(self, trace: Trace) -> list[Finding]:
        findings = []
        # Your deterministic analysis logic here
        return findings
```

3. Register the analyzer in `src/agentlint/analyzers/__init__.py`
4. Add tests in `tests/` with at least one trace that triggers the analyzer and one that doesn't
5. Document the analyzer in `docs/analyzers.md`

**Requirements for analyzers:**
- Must be **deterministic** — same input always produces same output
- Must use **zero API calls** — no LLM, no network
- Must run in **< 100ms** for a 50-step trace
- Must include clear, actionable finding messages

### Adding a Framework Adapter

Adapters convert framework-specific trace formats into AgentLint's universal schema.

1. Create a new file in `src/agentlint/ingest/`
2. Implement the `BaseAdapter` interface
3. Add example trace files in `tests/fixtures/`
4. Add tests that verify correct conversion

### Adding Test Traces

Good test traces are critical. To contribute traces:

1. Add JSON trace files to `tests/fixtures/`
2. Name them descriptively: `{framework}_{behavior}_{number}.json`
   - Example: `langgraph_infinite_loop_01.json`
   - Example: `crewai_healthy_search_01.json`
3. Include a brief comment in the test file explaining what the trace demonstrates

### Code Style

- We use `ruff` for linting and formatting
- We use `mypy` with strict mode for type checking
- All public functions need docstrings
- All analyzers need tests

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b add-new-analyzer`)
3. Write your code and tests
4. Ensure all tests pass (`pytest`)
5. Ensure linting passes (`ruff check src/ tests/`)
6. Submit a Pull Request with a clear description of what your change does and why

## Questions?

Open a [GitHub Discussion](https://github.com/YOUR_USERNAME/agentlint/discussions) or file an issue.
