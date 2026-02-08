# Phase 5.1: CLI Development - Shape

## Overview

Phase 5.1 adds a Typer-based CLI to Punie, enabling PyCharm to launch the agent as a subprocess via ACP stdio transport. The CLI respects the critical constraint that **stdout is reserved for ACP JSON-RPC** — all logging goes to files.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Entry Points                      │
│  • punie (script entry point)                            │
│  • python -m punie (__main__.py)                         │
│  • uvx punie (via [project.scripts])                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────┐
│                    src/punie/cli.py                       │
│                                                           │
│  app = typer.Typer()                                     │
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ resolve_model(flag) -> str                       │   │
│  │   CLI flag > PUNIE_MODEL env > "test" default   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ setup_logging(log_dir, level)                    │   │
│  │   RotatingFileHandler -> ~/.punie/logs/punie.log│   │
│  │   stderr handler at CRITICAL only                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ run_acp_agent(model, name) [async]               │   │
│  │   agent = PunieAgent(model, name)                │   │
│  │   run_agent(agent)  # from punie.acp.core        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ main() [@app.callback]                           │   │
│  │   Parse flags, setup logging, asyncio.run()      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────┐
│              src/punie/acp/core.py                        │
│  run_agent(agent) -> starts ACP stdio transport          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────┐
│            src/punie/acp/stdio.py                         │
│  stdio_streams() -> writes JSON-RPC to sys.stdout.buffer │
└─────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Pure Functions for Testability

- `resolve_model()` — no side effects, easy to test
- `setup_logging()` — isolated configuration, testable without async

### 2. Logging Strategy

**File-only logging:**
- `RotatingFileHandler` -> `~/.punie/logs/punie.log` (10MB max, 3 backups)
- Root logger level from `--log-level` flag
- **No stdout handler** — ACP requires exclusive stdout access

**Stderr handler:**
- CRITICAL level only
- For startup failures before logging is configured
- Writes to `sys.stderr`, not `sys.stdout`

### 3. Version Flag Behavior

```python
if version:
    typer.echo(f"punie {__version__}", err=True)  # stderr, not stdout
    raise typer.Exit(0)
```

### 4. Entry Point Structure

**Entry point:** `punie = "punie.cli:app"`
- Points to Typer app instance, not a function
- Typer's own runtime handles invocation
- `@app.callback(invoke_without_command=True)` makes bare `punie` run main()

### 5. Modern Agent Construction

```python
agent = PunieAgent(model=model, name=name)  # Not PydanticAgent(agent=...)
await run_agent(agent)
```

## CLI Flags

| Flag | Type | Default | Env Var | Notes |
|------|------|---------|---------|-------|
| `--model` | `str \| None` | None | `PUNIE_MODEL` | Resolved via `resolve_model()` |
| `--name` | `str` | `"punie-agent"` | — | Agent identification |
| `--log-dir` | `Path` | `~/.punie/logs/` | — | Log file directory |
| `--log-level` | `str` | `"info"` | — | Logging level |
| `--version` | `bool` | False | — | Print to stderr, exit |

## File Structure

```
src/punie/
├── cli.py              # NEW: Typer CLI (app, main, resolve_model, setup_logging, run_acp_agent)
├── __main__.py         # NEW: python -m punie support
├── __init__.py         # UNCHANGED: no CLI imports, avoid Typer for library users
└── acp/
    ├── core.py         # EXISTING: run_agent(agent)
    └── stdio.py        # EXISTING: stdout constraint

tests/
└── test_cli.py         # NEW: ~10 function-based tests

examples/
└── 11_cli_usage.py     # NEW: CLI utility demo

pyproject.toml          # MODIFIED: add typer dep, [project.scripts]
```

## Future Extensions (Phase 5.2-5.4)

Phase 5.1 uses `@app.callback(invoke_without_command=True)` to make bare `punie` run the ACP agent. Future phases add subcommands:

```python
@app.command()
def init():
    """Initialize ~/.punie configuration."""
    pass

@app.command()
def serve():
    """Run HTTP + ACP dual server."""
    pass
```

This design allows Phase 5.1 to ship a working `punie` command now, with subcommands added incrementally later.
