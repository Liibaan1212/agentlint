# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Core trace schema with Pydantic models (`Trace`, `Step`, `ToolCall`, `Observation`)
- Universal trace format specification
- Framework adapters: LangGraph, CrewAI, OpenTelemetry, Raw JSON
- Analyzers: Cycle detection, Tool efficiency, Hallucination signals, Progress monitor, Error cascade, Context waste
- CLI interface (`agentlint check`)
- Terminal reports with Rich formatting
- JSON report output
- Aggregate scoring engine
- Test suite with fixture traces
- Project documentation
