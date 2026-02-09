# Standards: Tool Performance Measurement

## Applicable Standards

### Python Standards
- **Dataclasses**: Use `@dataclass(frozen=True)` for immutable snapshots
- **Type hints**: Full type annotations, use `Literal` for string enums
- **Time measurement**: Use `time.monotonic()` for elapsed time (not affected by clock adjustments)

### Testing Standards
- **Function-based tests**: No test classes, use plain functions
- **Pytest fixtures**: Use fixtures for common setup
- **Assertions**: Use plain `assert` statements, pytest provides clear diffs

### Pydantic AI Integration
- **WrapperToolset**: Subclass `pydantic_ai.toolsets.wrapper.WrapperToolset` to intercept tool calls
- **Override `call_tool()`**: Timing logic in wrapper, original tools unchanged
- **Generic typing**: `WrapperToolset[ACPDeps]` maintains type safety

### CLI Standards
- **Click options**: Use `@click.option("--perf", is_flag=True)` for boolean flags
- **File output**: Write to current working directory with descriptive names
- **User feedback**: Print report location after generation

### HTML Report Standards
- **Standalone**: Embedded CSS, no external dependencies
- **Sections**: Summary → Details → Visualization
- **Accessibility**: Semantic HTML, proper table structure
- **Timestamps**: ISO format for clarity

## Code Organization

```
src/punie/perf/
├── __init__.py          # Public API exports
├── collector.py         # Data models + collector
├── toolset.py          # TimedToolset wrapper
└── report.py           # HTML generation

tests/
├── test_perf_collector.py
├── test_perf_toolset.py
├── test_perf_report.py
└── test_cli_perf.py
```

## Naming Conventions

- **Classes**: PascalCase (`ToolTiming`, `PerformanceCollector`)
- **Functions**: snake_case (`start_tool`, `generate_html_report`)
- **Constants**: UPPER_SNAKE_CASE (if needed)
- **Private attributes**: Leading underscore (`_tool_starts`)
