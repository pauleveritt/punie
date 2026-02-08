# Phase 5.1: CLI Development - References

## Key Files in Punie Codebase

### ACP Transport Files

| File | Lines | Purpose | Relevance |
|------|-------|---------|-----------|
| `src/punie/acp/stdio.py` | 30-45 | `stdio_streams()` — writes JSON-RPC to `sys.stdout.buffer` | **Critical:** Why stdout is off-limits |
| `src/punie/acp/core.py` | 75-90 | `run_agent(agent)` — starts ACP agent loop | **Direct call:** CLI invokes this |
| `src/punie/acp/agent_card.py` | 1-50 | Agent card structure for ACP | Shows agent metadata structure |

### Agent Construction Files

| File | Lines | Purpose | Relevance |
|------|-------|---------|-----------|
| `src/punie/agent/adapter.py` | 40-80 | `PunieAgent(model, name)` constructor | **Modern API:** How CLI constructs agents |
| `tests/fixtures/minimal_agent.py` | 15-30 | `@pytest.fixture punie_agent` | Pattern to follow for CLI wiring |

### Existing Model Resolution

| File | Lines | Purpose | Relevance |
|------|-------|---------|-----------|
| `src/punie/agent/adapter.py` | 45-55 | `model: str = os.getenv("PUNIE_MODEL", "test")` | Shows env var pattern to extend |

### HTTP Runner (Future Reference)

| File | Lines | Purpose | Relevance |
|------|-------|---------|-----------|
| `src/punie/http/runner.py` | 60-80 | `run_dual(agent, http_port, acp_port)` | Phase 5.4: `punie serve` will use this |

## External References

### Typer Documentation

- **Quickstart:** https://typer.tiangolo.com/tutorial/first-steps/
- **Callbacks:** https://typer.tiangolo.com/tutorial/commands/callback/
  - `@app.callback(invoke_without_command=True)` pattern
- **Echo to stderr:** https://typer.tiangolo.com/tutorial/printing/#printing-to-standard-error
  - `typer.echo(msg, err=True)`
- **Testing:** https://typer.tiangolo.com/tutorial/testing/
  - `typer.testing.CliRunner` usage

### Python Packaging

- **Entry Points:** https://packaging.python.org/en/latest/specifications/entry-points/
  - `[project.scripts]` specification
- **`__main__.py`:** https://docs.python.org/3/library/__main__.html
  - How `python -m package` works

### Logging Best Practices

- **RotatingFileHandler:** https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler
  - `maxBytes=10*1024*1024` (10MB), `backupCount=3`
- **Logger Propagation:** https://docs.python.org/3/howto/logging.html#logging-flow
  - How root logger affects all loggers

### ACP Protocol

- **Agent Communication Protocol:** Internal doc at `docs/research/acp-reference.md`
  - Stdio transport: JSON-RPC over stdin/stdout
  - Why stdout must be exclusive to protocol

## Comparison: CLI Entry Point Patterns

### Pattern 1: Function Entry Point (Not Used)

```toml
[project.scripts]
punie = "punie.cli:main"  # Points to function
```

```python
def main():
    app()  # Manually invoke Typer
```

**Pros:** Explicit control
**Cons:** Extra layer, Typer already handles this

### Pattern 2: App Entry Point (Chosen)

```toml
[project.scripts]
punie = "punie.cli:app"  # Points to Typer app
```

```python
app = typer.Typer()

@app.callback(invoke_without_command=True)
def main():
    # Runs when no subcommand given
    pass
```

**Pros:** Idiomatic Typer, subcommands just work
**Cons:** None

**Decision:** Use Pattern 2 — cleaner, supports future subcommands.

## Comparison: Logging Strategies

### Strategy 1: File Only (Chosen)

```python
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3)
root_logger.addHandler(handler)
root_logger.setLevel(log_level)
```

**Pros:** No stdout pollution, simple
**Cons:** Can't see logs during development (but `tail -f ~/.punie/logs/punie.log` works)

### Strategy 2: File + Stderr (Not Used)

```python
file_handler = RotatingFileHandler(...)
stderr_handler = logging.StreamHandler(sys.stderr)
root_logger.addHandler(file_handler)
root_logger.addHandler(stderr_handler)
```

**Pros:** See logs in terminal
**Cons:** PyCharm sees stderr, may confuse ACP client

**Decision:** Strategy 1 for Phase 5.1. Strategy 2 could be added in 5.2 via `--verbose` flag if needed.

### Strategy 3: Conditional (Not Used Yet)

```python
if sys.stdin.isatty():
    # Interactive mode — add stderr handler
else:
    # Subprocess mode — file only
```

**Pros:** Best of both worlds
**Cons:** Complexity, harder to test

**Decision:** Defer to Phase 5.2 if needed. Keep 5.1 simple.

## Example: Existing CLI Projects

### Project: `ruff`

- Entry point: `ruff = "ruff:main"`
- Logging: stderr only (no protocol constraint)
- Version: `ruff --version` (stdout)

**Lesson:** We can't follow Ruff's stdout pattern due to ACP.

### Project: `uvx`

- Part of `uv` CLI
- Subprocess pattern: launches tools as subprocesses
- Logging: file-based for daemon

**Lesson:** Similar subprocess model — file logging is standard.

### Project: Pydantic AI (Internal)

- No CLI (library only)
- Agent construction: `agent = Agent(model=...)`

**Lesson:** Our `PunieAgent(model, name)` follows same pattern.

## Roadmap Context

### Phase 5.0: ACP Core (Complete)

- `run_agent(agent)` — what CLI will call
- `stdio_streams()` — stdout constraint origin

### Phase 5.1: CLI Development (Current)

- Bare `punie` command
- ACP stdio agent startup
- File-only logging

### Phase 5.2: Configuration Management (Next)

- `punie init` — create `~/.punie/config.toml`
- `punie status` — show config/logs
- Config file parsing

### Phase 5.3: IDE Tool Integration (Future)

- Dynamic tool discovery via filesystem
- Tool registration with ACP
- `punie tools list` command

### Phase 5.4: HTTP Server (Future)

- `punie serve` — HTTP + ACP dual server
- Web UI for agent interaction
- Uses `run_dual()` from `http/runner.py`

## Related Issues/Decisions

### Decision: No Click, Use Typer

**Context:** Click is the underlying library for Typer.

**Decision:** Use Typer, not Click directly.

**Rationale:**
- Typer provides type hints (better DX)
- Automatic help generation from annotations
- Rich integration path (future)
- Maintained by same author as FastAPI

### Decision: No `rich` in Phase 5.1

**Context:** Typer supports Rich for pretty output.

**Decision:** No Rich until Phase 5.2.

**Rationale:**
- Rich writes to stdout by default
- Phase 5.1 can't use stdout (ACP protocol)
- Phase 5.2 adds commands (`init`, `status`) that can use stdout

### Decision: `~/.punie/logs/` Location

**Context:** Where to write log files?

**Options:**
1. `~/.punie/logs/` (chosen)
2. `~/.local/share/punie/logs/` (XDG)
3. `~/.cache/punie/logs/` (XDG cache)

**Decision:** Option 1 — simplest, matches existing conventions.

**Future:** Phase 5.2 could add XDG support via `platformdirs` library.

## Testing References

### Typer Testing Patterns

```python
from typer.testing import CliRunner

runner = CliRunner()

def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "punie" in result.stderr  # stderr, not stdout
```

### Logging Test Patterns

```python
@pytest.fixture(autouse=True)
def clean_root_logger():
    """Remove all handlers from root logger after test."""
    yield
    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()
        root.removeRemoveHandler(handler)

def test_setup_logging_creates_directory(tmp_path):
    log_dir = tmp_path / "logs"
    setup_logging(log_dir, "info")
    assert (log_dir / "punie.log").exists()
```

### Environment Variable Testing

```python
def test_resolve_model_env_var_fallback(monkeypatch):
    monkeypatch.setenv("PUNIE_MODEL", "claude-3-5-sonnet")
    assert resolve_model(None) == "claude-3-5-sonnet"

def test_resolve_model_default(monkeypatch):
    monkeypatch.delenv("PUNIE_MODEL", raising=False)
    assert resolve_model(None) == "test"
```

## Summary

Phase 5.1 builds on:
- **ACP stdio transport** (Phase 5.0) — stdout constraint
- **Modern agent construction** (Phase 3.4) — `PunieAgent(model, name)`
- **Existing env var pattern** (adapter.py) — `PUNIE_MODEL`

Phase 5.1 enables:
- **Phase 5.2** — config management (`punie init`)
- **Phase 5.3** — IDE tools (`punie tools list`)
- **Phase 5.4** — dual server (`punie serve`)

The critical constraint (stdout reserved for ACP) shapes all logging decisions.
