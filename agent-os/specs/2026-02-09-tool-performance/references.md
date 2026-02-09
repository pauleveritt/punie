# References: Tool Performance Measurement

## Internal Code References

### Existing Patterns

1. **ToolCallTracker** (`src/punie/diagnostic/tool_call_tracker.py`)
   - Mutable collector pattern
   - `start_tool()` / `end_tool()` lifecycle
   - Frozen dataclass for results
   - **Inspiration for PerformanceCollector design**

2. **ACPDeps** (`src/punie/agent/deps.py`)
   - Generic type parameter for toolset
   - Dependency injection pattern
   - **Used in `TimedToolset[ACPDeps]` typing**

3. **create_local_agent()** (`src/punie/agent/factory.py`)
   - Agent factory function
   - Creates toolset from tools
   - **Location to add perf_collector parameter**

4. **CLI ask command** (`src/punie/cli.py`)
   - Click command definition
   - Agent lifecycle management
   - **Location to add --perf flag**

### Pydantic AI References

1. **WrapperToolset** (`pydantic_ai.toolsets.wrapper`)
   - Base class for toolset wrappers
   - Override `call_tool()` method
   - Generic over dependencies type

2. **FunctionToolset** (used in `toolset.py`)
   - Creates toolset from function list
   - What we're wrapping with `TimedToolset`

## External References

### Python Standard Library

- `time.monotonic()` — Monotonic clock for elapsed time measurement
- `dataclasses.dataclass` — Frozen dataclasses for immutable data
- `typing.Literal` — String literal types for backend

### Testing

- `pytest` — Test framework
- `pytest.fixture` — Test fixtures for setup

## Documentation Links

- Pydantic AI Toolsets: https://ai.pydantic.dev/toolsets/
- Python time module: https://docs.python.org/3/library/time.html#time.monotonic
- Dataclasses: https://docs.python.org/3/library/dataclasses.html
