# Phase 7: Tool Performance Measurement

## Context

Punie supports both IDE tools (via ACP/PyCharm) and local tools (via LocalClient). Both backends use the same 7 tool functions in `toolset.py` — the only difference is the `Client` implementation behind `ctx.deps.client_conn`. We need a developer diagnostic that captures elapsed time per tool call during prompt execution and generates an HTML report. This will help understand performance characteristics and identify optimization opportunities.

**Key design insight:** Pydantic AI provides `WrapperToolset` (`pydantic_ai.toolsets.wrapper`) with an overridable `call_tool()` method. We can wrap the existing toolset to add timing without modifying any tool function code.

## Plan

### Task 1: Save spec documentation

Create `agent-os/specs/2026-02-09-tool-performance/` with:
- `plan.md` — This full plan
- `shape.md` — Shaping notes, data structures, file changes
- `standards.md` — Applicable standards
- `references.md` — Internal references

### Task 2: Create data model and collector (`src/punie/perf/`)

New package `src/punie/perf/` with:

**`src/punie/perf/__init__.py`** — Public API exports

**`src/punie/perf/collector.py`** — Mutable collector + frozen data model:
- `ToolTiming` frozen dataclass: `tool_name`, `started_at` (float, monotonic), `ended_at`, `duration_ms`, `success`, `error`
- `PromptTiming` frozen dataclass: `started_at`, `ended_at`, `duration_ms`, `model_name`, `backend` (literal "local"|"ide"), `tool_timings` (tuple of ToolTiming)
- `PerformanceCollector` mutable class (follows ToolCallTracker pattern):
  - `start_tool(name)` → records monotonic start time
  - `end_tool(name, success=True, error=None)` → creates ToolTiming, appends to internal list
  - `start_prompt(model_name, backend)` / `end_prompt()` → records overall timing
  - `report()` → returns frozen `PromptTiming` snapshot

**Tests:** `tests/test_perf_collector.py` — Function-based tests for collector lifecycle, timing accuracy, frozen snapshots

### Task 3: Create `TimedToolset` wrapper (`src/punie/perf/toolset.py`)

Subclass `WrapperToolset` to intercept all tool calls:

```python
@dataclass
class TimedToolset(WrapperToolset[ACPDeps]):
    collector: PerformanceCollector

    async def call_tool(self, name, tool_args, ctx, tool):
        self.collector.start_tool(name)
        try:
            result = await self.wrapped.call_tool(name, tool_args, ctx, tool)
            self.collector.end_tool(name, success=True)
            return result
        except Exception as exc:
            self.collector.end_tool(name, success=False, error=str(exc))
            raise
```

This wraps any `FunctionToolset` without modifying tool functions.

**Tests:** `tests/test_perf_toolset.py` — Test that TimedToolset records timing around tool calls using a fake toolset

### Task 4: Generate HTML report (`src/punie/perf/report.py`)

Pure function: `generate_html_report(timing: PromptTiming) -> str`

- Standalone HTML with embedded CSS (no external dependencies)
- Sections:
  - **Summary**: model name, backend label, total prompt duration, total tool time vs. model think time
  - **Tool calls table**: tool name, duration (ms), success/failure, ordered by execution time
  - **Timing breakdown**: simple bar visualization showing tool vs. model time
- Report includes timestamp and backend label for cross-run comparison

**Tests:** `tests/test_perf_report.py` — Test HTML generation with known PromptTiming data, verify structure

### Task 5: Wire into CLI (`src/punie/cli.py`)

Add `--perf` flag and `PUNIE_PERF` env var to `punie ask` command:

1. When `--perf` is passed or `PUNIE_PERF=1` is set:
   - Create `PerformanceCollector()`
   - Wrap the toolset: `TimedToolset(wrapped=toolset, collector=collector)` in `create_local_agent()`
   - Call `collector.start_prompt()` before `agent.run()`, `collector.end_prompt()` after
   - Generate HTML report, write to `punie-perf-{timestamp}.html` in cwd
   - Print path to report

2. Priority: `--perf` flag > `PUNIE_PERF` env var > False default

**Modifications to `create_local_agent()`** in `factory.py`:
- Add optional `perf_collector: PerformanceCollector | None = None` parameter
- When provided, wrap the toolset with `TimedToolset` before passing to agent

**New function `resolve_perf()`**:
- Resolves perf from CLI flag or `PUNIE_PERF` env var
- Follows same pattern as `resolve_model()` and `resolve_mode()`

**Tests:** `tests/test_cli_perf.py` — Test `--perf` flag and `PUNIE_PERF` env var produce HTML file

## Files to create

| File | Purpose |
|------|---------|
| `src/punie/perf/__init__.py` | Public exports |
| `src/punie/perf/collector.py` | ToolTiming, PromptTiming, PerformanceCollector |
| `src/punie/perf/toolset.py` | TimedToolset (WrapperToolset subclass) |
| `src/punie/perf/report.py` | generate_html_report() pure function |
| `tests/test_perf_collector.py` | Collector tests |
| `tests/test_perf_toolset.py` | TimedToolset tests |
| `tests/test_perf_report.py` | HTML report tests |
| `tests/test_cli_perf.py` | CLI --perf flag tests |

## Files to modify

| File | Change |
|------|--------|
| `src/punie/agent/factory.py` | Add `perf_collector` param to `create_local_agent()`, wrap toolset |
| `src/punie/cli.py` | Add `--perf` flag to `ask` command, collector lifecycle |

## Verification

1. `uv run ruff check src/punie/perf/ tests/test_perf_*.py tests/test_cli_perf.py`
2. `uv run ruff format --check src/punie/perf/ tests/test_perf_*.py tests/test_cli_perf.py`
3. `uv run ty check src/punie/perf/`
4. `uv run pytest tests/test_perf_collector.py tests/test_perf_toolset.py tests/test_perf_report.py tests/test_cli_perf.py -v`
5. `uv run pytest` (full suite, ensure nothing broken)
6. Manual: `punie ask "How many Python files are here?" --perf` → produces HTML file
