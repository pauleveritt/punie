# Phase 5.1: Typer-based CLI with uvx Support - Implementation Plan

## Context

Punie currently has **no CLI entry point** — no `[project.scripts]`, no `__main__.py`. The only way to run the agent is programmatically via test fixtures (`tests/fixtures/minimal_agent.py`). PyCharm needs to launch Punie as a subprocess via `acp.json`, which requires a `punie` command that starts the ACP stdio agent. Phase 5.1 adds this minimal CLI.

## Critical Constraint

**stdout is reserved for ACP JSON-RPC.** The ACP stdio transport writes raw bytes to `sys.stdout.buffer` (see `src/punie/acp/stdio.py`). Any logging or output to stdout corrupts the protocol. All logging MUST go to files only. Even `--version` must write to stderr.

## Implementation Tasks

### Task 1: Save spec documentation ✓

Create `agent-os/specs/2026-02-08-cli-development/` with plan.md, shape.md, standards.md, references.md.

### Task 2: Add Typer dependency and entry point

**Modify:** `pyproject.toml`

- Add `typer>=0.15.0` to `dependencies` (runtime dep, required for `uvx punie`)
- Add `[project.scripts]` section:

```toml
[project.scripts]
punie = "punie.cli:app"
```

### Task 3: Create CLI module

**New file:** `src/punie/cli.py`

Structure:
- `app = typer.Typer(...)` — the Typer app (also the entry point)
- `resolve_model(model_flag) -> str` — pure function: CLI flag > `PUNIE_MODEL` env var > `"test"` default
- `setup_logging(log_dir, log_level)` — pure function: configures `RotatingFileHandler` to `~/.punie/logs/punie.log`, never touches stdout
- `run_acp_agent(model, name)` — async function: creates `PunieAgent(model=model, name=name)`, calls `run_agent(agent)` from `punie.acp`
- `main()` — Typer callback (`@app.callback(invoke_without_command=True)`): parses flags, calls `setup_logging()`, calls `asyncio.run(run_acp_agent(...))`

**CLI flags:**
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--model` | `str \| None` | None (resolves via env/default) | Model name, overrides PUNIE_MODEL env var |
| `--name` | `str` | `"punie-agent"` | Agent name for identification |
| `--log-dir` | `Path` | `~/.punie/logs/` | Directory for log files |
| `--log-level` | `str` | `"info"` | Logging level |
| `--version` | `bool` | False | Print version to **stderr** and exit |

### Task 4: Create `__main__.py`

**New file:** `src/punie/__main__.py`

```python
"""Support for `python -m punie` invocation."""
from punie.cli import app
app()
```

### Task 5: Write tests

**New file:** `tests/test_cli.py`

~10 function-based tests covering:
- Pure function tests: `resolve_model()`, `setup_logging()`
- Typer CliRunner tests: `--version`, `--help`

### Task 6: Verify existing tests pass

Run `uv run pytest tests/` — all ~124 existing tests must still pass.

### Task 7: Create example

**New file:** `examples/11_cli_usage.py`

Demonstrates `resolve_model()` and `setup_logging()` programmatically.

### Task 8: Update roadmap and evolution docs

- Mark 5.1 complete in `agent-os/product/roadmap.md`
- Add Phase 5.1 section to `docs/research/evolution.md`

## Verification Steps

1. `uv run ty check src/punie/cli.py` — type checking
2. `uv run ruff check src/punie/cli.py tests/test_cli.py` — linting
3. `uv run pytest tests/` — all tests pass
4. `uv run python -m punie --version` — prints version to stderr
5. `uv run python -m punie --help` — shows help text
6. `uv run punie --version` — works via entry point

## Success Criteria

- ✓ CLI entry point works: `punie`, `python -m punie`, `uvx punie`
- ✓ All logging goes to files, not stdout
- ✓ `--version` writes to stderr
- ✓ All existing tests pass
- ✓ Type checking passes
- ✓ Linting passes
