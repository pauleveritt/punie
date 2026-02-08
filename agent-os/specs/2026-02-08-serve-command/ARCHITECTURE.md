# Architecture: Serve Command

## Component Structure

```
src/punie/cli.py
├── run_serve_agent(model, name, host, port, log_level) [async]
└── @app.command() def serve(...)
```

## Existing Dependencies (Reused)

From `punie.agent.adapter`:
- `PunieAgent(model, name)` — agent implementation

From `punie.http.app`:
- `create_app()` — Starlette app factory

From `punie.http.runner`:
- `run_dual(agent, app, host, port, log_level)` — concurrent stdio + HTTP

From `punie.http.types`:
- `Host`, `Port` — NewType wrappers for network config

## Async Helper Function

### `async def run_serve_agent(model, name, host, port, log_level)`

**Purpose:** Create agent and app, delegate to run_dual()

**Logic:**
1. Create `PunieAgent(model, name)`
2. Create Starlette app with `create_app()`
3. Wrap host/port in NewType constructors
4. Call `await run_dual(agent, app, host, port, log_level)`

**Why separate function?**
- Typer commands must be sync (no async def)
- Allows testing async logic without CliRunner complexity
- Clean separation of Typer concerns from async execution

## Typer Command

### `@app.command() def serve(...)`

**Parameters:**
- `--host` (default `127.0.0.1`): HTTP server bind address
- `--port` (default `8000`): HTTP server port
- `--model` (optional): Model name (same as main command)
- `--name` (default `punie-agent`): Agent name
- `--log-dir` (default `~/.punie/logs`): Log directory
- `--log-level` (default `info`): Logging level

**Flow:**
1. Setup logging with `setup_logging()`
2. Resolve model with `resolve_model()`
3. Print startup message to stdout (ALLOWED for serve command)
4. Call `asyncio.run(run_serve_agent(...))`

**Output:**
```
Starting Punie agent (dual protocol mode)
  Model: claude-sonnet-4-5-20250929
  HTTP: http://127.0.0.1:8000
  Logs: ~/.punie/logs/punie.log

[Agent starts, stdio reserved for ACP from here]
```

## Protocol Behavior

**Before agent starts:**
- stdout available for setup messages
- User-facing output with typer.echo()

**After agent starts:**
- stdout owned by ACP JSON-RPC
- HTTP runs on separate port
- All logs to files

## Dependencies

**New imports in cli.py:**
```python
from punie.http.app import create_app
from punie.http.runner import run_dual
from punie.http.types import Host, Port
```

**No new packages** — all existing infrastructure
