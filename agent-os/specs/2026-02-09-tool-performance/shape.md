# Shape: Tool Performance Measurement

## Data Structures

### ToolTiming (frozen dataclass)
```python
@dataclass(frozen=True)
class ToolTiming:
    tool_name: str
    started_at: float  # monotonic time
    ended_at: float
    duration_ms: float
    success: bool
    error: str | None = None
```

### PromptTiming (frozen dataclass)
```python
@dataclass(frozen=True)
class PromptTiming:
    started_at: float
    ended_at: float
    duration_ms: float
    model_name: str
    backend: Literal["local", "ide"]
    tool_timings: tuple[ToolTiming, ...]
```

### PerformanceCollector (mutable class)
```python
class PerformanceCollector:
    _tool_starts: dict[str, float]
    _tool_timings: list[ToolTiming]
    _prompt_start: float | None
    _prompt_info: tuple[str, str] | None  # (model_name, backend)

    def start_tool(self, name: str) -> None: ...
    def end_tool(self, name: str, success: bool = True, error: str | None = None) -> None: ...
    def start_prompt(self, model_name: str, backend: Literal["local", "ide"]) -> None: ...
    def end_prompt(self) -> None: ...
    def report(self) -> PromptTiming: ...
```

## File Changes

### New Files

1. **src/punie/perf/__init__.py**
   - Export: `ToolTiming`, `PromptTiming`, `PerformanceCollector`, `TimedToolset`, `generate_html_report`

2. **src/punie/perf/collector.py**
   - Define frozen dataclasses: `ToolTiming`, `PromptTiming`
   - Define mutable collector: `PerformanceCollector`
   - Uses `time.monotonic()` for timing

3. **src/punie/perf/toolset.py**
   - Define `TimedToolset(WrapperToolset[ACPDeps])`
   - Override `call_tool()` to record timing
   - Generic enough to work with any toolset

4. **src/punie/perf/report.py**
   - Pure function: `generate_html_report(timing: PromptTiming) -> str`
   - Embedded CSS, no external dependencies
   - Sections: Summary, Tool Calls Table, Timing Breakdown

### Modified Files

1. **src/punie/agent/factory.py**
   - Add optional parameter: `perf_collector: PerformanceCollector | None = None`
   - When provided, wrap toolset: `TimedToolset(wrapped=toolset, collector=perf_collector)`

2. **src/punie/cli.py**
   - Add `--perf` flag to `ask` command
   - Create collector, pass to factory
   - Call `start_prompt()` before `agent.run()`
   - Call `end_prompt()` after
   - Generate and save HTML report

## Integration Flow

```
CLI (--perf flag or PUNIE_PERF=1 env var)
  ↓
resolve_perf() checks flag > env var > default
  ↓
Create PerformanceCollector (if enabled)
  ↓
Pass to create_local_agent(perf_collector=collector)
  ↓
Factory wraps toolset with TimedToolset
  ↓
Agent runs, tools called through TimedToolset
  ↓
TimedToolset records timing for each call
  ↓
CLI calls collector.report()
  ↓
Generate HTML report
  ↓
Write to punie-perf-{timestamp}.html
```

## Environment Variable

**`PUNIE_PERF`** - Enable performance reporting
- Set to `"1"` to enable
- Any other value (including `"0"` or unset) disables
- Useful for ACP mode via `acp.json`:
  ```json
  {
    "agent_servers": {
      "punie": {
        "command": "punie",
        "env": {
          "PUNIE_PERF": "1"
        }
      }
    }
  }
  ```

## Key Design Decisions

1. **Use WrapperToolset**: Avoids modifying tool functions, clean separation of concerns
2. **Frozen dataclasses for snapshots**: Immutable results prevent accidental mutation
3. **Mutable collector**: Follows ToolCallTracker pattern, easy to use during execution
4. **Monotonic time**: Prevents clock adjustments from affecting measurements
5. **Embedded CSS in HTML**: Single-file report, easy to share and view
6. **Backend label**: Distinguishes local vs IDE performance characteristics
