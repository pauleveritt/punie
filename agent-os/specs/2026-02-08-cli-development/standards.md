# Phase 5.1: CLI Development - Standards

## Coding Standards

### 1. Logging Discipline

**Rule:** Never write to stdout in CLI code.

**Rationale:** ACP stdio transport owns `sys.stdout.buffer`. Any other output corrupts JSON-RPC messages.

**Implementation:**
```python
# CORRECT: Log to file
logging.getLogger(__name__).info("Agent started")

# CORRECT: Version to stderr
typer.echo(f"punie {__version__}", err=True)

# WRONG: Prints to stdout
print("Starting agent...")
typer.echo("Agent started")  # defaults to stdout
```

### 2. Pure Functions First

**Rule:** Separate pure logic from side effects.

**Rationale:** Makes code testable without mocking async/IO.

**Structure:**
```python
# Pure function: no async, no I/O, easy to test
def resolve_model(model_flag: str | None) -> str:
    if model_flag:
        return model_flag
    return os.getenv("PUNIE_MODEL", "test")

# Side-effect function: separate, test differently
def setup_logging(log_dir: Path, log_level: str) -> None:
    # Configuration side effects here
    pass

# Async function: depends on pure functions
async def run_acp_agent(model: str, name: str) -> None:
    agent = PunieAgent(model=model, name=name)
    await run_agent(agent)
```

### 3. Test Organization

**Rule:** Function-based tests, organized by concern.

**Structure:**
```python
# Pure function tests (no Typer, no async)
def test_resolve_model_flag_takes_priority():
    assert resolve_model("claude-3-5-sonnet") == "claude-3-5-sonnet"

def test_setup_logging_creates_directory(tmp_path):
    setup_logging(tmp_path / "logs", "info")
    assert (tmp_path / "logs" / "punie.log").exists()

# Typer CliRunner tests
def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "punie 0.1.0" in result.stderr
```

### 4. Flag Naming

**Rule:** Use long-form `--flags`, avoid short forms initially.

**Rationale:** Clarity over brevity for v0.1.0. Short forms (`-m`, `-v`) can be added later if needed.

**Examples:**
- ✓ `--model`, `--name`, `--log-dir`
- ✗ `-m`, `-n`, `-l` (not yet, maybe in 5.2+)

### 5. Entry Point Convention

**Rule:** Entry point points to Typer app instance, not a function.

```toml
[project.scripts]
punie = "punie.cli:app"  # CORRECT: Typer app
# punie = "punie.cli:main"  # WRONG: main() is callback, not entry
```

**Rationale:** Typer's runtime handles argument parsing and invocation.

### 6. Version Reading

**Rule:** Read version from `punie.__version__`, not inline strings.

```python
from punie import __version__

@app.callback()
def main(version: bool = False):
    if version:
        typer.echo(f"punie {__version__}", err=True)  # Single source of truth
```

### 7. Error Handling

**Rule:** Let exceptions propagate to Typer's handler in initial phase.

**Rationale:** Typer provides good default error messages. Custom error handling added in Phase 5.2 if needed.

**Non-requirement for 5.1:**
```python
# Not required yet — Typer handles this
try:
    await run_acp_agent(model, name)
except Exception as e:
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(1)
```

### 8. Path Expansion

**Rule:** Expand user paths (`~`) in setup code, not defaults.

```python
@app.callback()
def main(
    log_dir: Path = Path("~/.punie/logs"),  # User tilde
):
    log_dir = log_dir.expanduser()  # Expand before use
    setup_logging(log_dir, log_level)
```

## Testing Standards

### Test Coverage Requirements

**Pure functions:** 100% — easy to test, no excuses
- `resolve_model()` — all 3 branches (flag, env, default)
- `setup_logging()` — directory creation, handler config, no stdout

**Typer CLI:** Basic smoke tests
- `--version` works, writes to stderr
- `--help` shows help text
- Exit codes correct

**Not required in 5.1:**
- Integration tests (agent actually starts) — too slow, test via `acp.test_core.py`
- Error path tests (bad models, permission errors) — defer to Phase 5.2

### Fixture Discipline

**Rule:** Clean up logging handlers after tests.

```python
@pytest.fixture(autouse=True)
def clean_root_logger():
    """Remove all handlers from root logger after test."""
    yield
    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)
```

**Rationale:** `setup_logging()` modifies global state (root logger). Tests must not leak handlers.

## Documentation Standards

### Docstring Style

**Module docstring:**
```python
"""Typer-based CLI for Punie.

Critical constraint: stdout is reserved for ACP JSON-RPC. All logging
goes to files (~/.punie/logs/punie.log). Version info prints to stderr.
"""
```

**Function docstrings:** Only for exported functions with non-obvious behavior.
```python
def resolve_model(model_flag: str | None) -> str:
    """Resolve model name from CLI flag, env var, or default.

    Priority: CLI flag > PUNIE_MODEL env var > "test" default.
    """
```

**No docstrings needed for:** `main()`, `run_acp_agent()` — behavior clear from code.

### Example Standards

**Rule:** Examples demonstrate real-world usage, not trivial calls.

**Structure:**
```python
"""Example: CLI utility usage.

Demonstrates model resolution and logging setup programmatically.
"""

if __name__ == "__main__":
    # Model resolution examples
    model = resolve_model(None)  # Uses env/default
    print(f"Model: {model}")

    # Logging setup
    setup_logging(Path.home() / ".punie" / "logs", "debug")
    logging.info("Logging configured")
```

## Dependency Standards

### Runtime Dependencies

**Rule:** Minimize runtime deps. Typer is acceptable because:
- Required for CLI functionality (can't defer)
- Stable, mature library (0.15.0+)
- No heavy transitive deps
- Users who import `punie` as a library don't pay Typer import cost (not imported in `__init__.py`)

### Constraint: No Rich (Yet)

**Rule:** Avoid adding `rich` dependency in Phase 5.1.

**Rationale:** Typer supports Rich for pretty output, but that goes to stdout. Phase 5.1 writes nothing to stdout. Defer Rich to Phase 5.2 for `punie init`, `punie status` where stdout is available.

## Version Standard

**Rule:** Single source of truth for version.

```python
# src/punie/__init__.py
__version__ = "0.1.0"

# src/punie/cli.py
from punie import __version__

# pyproject.toml (if using dynamic version)
[project]
dynamic = ["version"]  # Optional: could use hatch-vcs in future
```

**Phase 5.1:** Keep version in `__init__.py`. Dynamic versioning via `hatch-vcs` deferred to Phase 6 (packaging).
