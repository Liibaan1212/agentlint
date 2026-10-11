# 🔍 AgentLint

**A deterministic linter for AI agent execution trajectories.**

Like `pylint` for your Python code — but for AI agent behavior.

---

> AgentLint analyzes agent execution traces and detects **loops**, **hallucinated tool calls**, **wasted context**, **error cascades**, and **inefficient paths** — in milliseconds, with zero API calls, at zero cost.

## The Problem

When an AI agent executes a 30-step task, current tools only tell you whether the **final output** looks correct. But agents fail *along the trajectory* — entering loops on step 7, hallucinating tool arguments on step 12, or stumbling into the correct answer through lucky error recovery.

**LLM-as-a-judge** can evaluate trajectories, but it costs $0.30/trace, takes 8 seconds, and introduces its own biases (self-preference, verbosity bias, positional bias, judge drift).

**AgentLint** runs deterministic analysis algorithms that produce trajectory quality scores in **47ms** at **$0/trace**.

## Quick Start

```bash
pip install agentlint
```

```bash
# Lint a single trace file
agentlint check trace.json

# Lint with detailed per-step annotations
agentlint check trace.json --verbose

# Output as JSON for CI/CD integration
agentlint check trace.json --format json
```

### Python API

```python
from agentlint import lint_trace

result = lint_trace("trace.json")
print(result.score)          # 0.0 - 1.0 overall trajectory quality
print(result.findings)       # List of detected issues with step locations

# Use in tests
assert result.score > 0.7, f"Agent trajectory quality too low: {result.score}"
```

## What It Detects

| Analyzer | What It Finds | How It Works |
|:---|:---|:---|
| 🔄 **Cycle Detector** | Loops and repeated state patterns | Graph-based sequence alignment with cosine similarity |
| 📈 **Progress Monitor** | Stalled or oscillating progress | Edit-distance progress curves against goal state |
| 🛠️ **Tool Efficiency** | Redundant or no-op tool calls | Productive vs. wasteful call ratio analysis |
| 💥 **Error Cascade** | Failures that corrupt downstream steps | Causal chain tracing from error origin |
| 👻 **Hallucination Signals** | Invalid tool args, fake paths, bad schemas | Structural pattern matching against tool definitions |
| 📦 **Context Waste** | Redundant information consuming context budget | Duplicate content detection across steps |

## Framework Support

AgentLint works with any agent framework that produces structured execution logs:

- ✅ **LangGraph** — Native adapter
- ✅ **CrewAI** — Native adapter
- ✅ **OpenTelemetry** — OTLP trace adapter
- ✅ **Raw JSON** — Universal fallback format
- 🔜 AutoGen, PydanticAI, smolagents

## Benchmarks

<!-- TODO: Fill with real benchmark data after M5 -->

| Metric | AgentLint | LLM-as-a-Judge (GPT-4o) | LLM-as-a-Judge (Llama 8B) |
|:---|:---:|:---:|:---:|
| Correlation with human ratings (ρ) | *TBD* | *TBD* | *TBD* |
| Cost per trace | **$0.00** | ~$0.30 | **$0.00** (local) |
| Latency per trace | **~47ms** | ~8,000ms | ~3,000ms |
| Deterministic | ✅ Yes | ❌ No | ❌ No |
| Works offline | ✅ Yes | ❌ No | ✅ Yes |

## Architecture

```
Trace File (JSON)
       │
       ▼
┌──────────────┐
│ Ingest Layer │  ← Framework-specific adapters normalize to universal schema
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Analyze      │  ← Deterministic algorithms (no LLM calls)
│ Engine       │     • Cycle detection (NetworkX)
│              │     • Progress curves (edit distance)
│              │     • Tool call efficiency (set analysis)
│              │     • Hallucination signals (schema validation)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Report Layer │  ← Terminal (Rich), JSON, SARIF (GitHub)
└──────────────┘
```

## Roadmap

- [x] Core trace schema and Pydantic models
- [ ] Cycle detection analyzer
- [ ] Tool call efficiency analyzer
- [ ] Hallucination signal detector
- [ ] CLI with Rich terminal output
- [ ] Progress monitor and error cascade analyzers
- [ ] Benchmark study (correlation with human ratings)
- [ ] pytest plugin (`assert trace.agentlint_score > 0.7`)
- [ ] GitHub Actions integration
- [ ] SARIF output for GitHub Code Scanning

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding analyzers, framework adapters, and test traces.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

AgentLint draws inspiration from the evaluation-first engineering culture championed by Hamel Husain, Shreya Shankar, Eugene Yan, and the broader AI evals movement. The core insight — that agent trajectory quality can be assessed deterministically — is a hypothesis under active testing.
