# Implementation Plan: Serve Command

## Changes to `src/punie/cli.py`

### Imports to Add

```python
from punie.http.app import create_app
from punie.http.runner import run_dual
from punie.http.types import Host, Port
```

### Async Helper Function

```python
async def run_serve_agent(
    model: str,
    name: str,
    host: str,
    port: int,
    log_level: str,
) -> None:
    """Create agent and run dual-protocol mode.

    Args:
        model: Model name for agent
        name: Agent name for identification
        host: HTTP server bind address
        port: HTTP server port
        log_level: Logging level for HTTP server
    """
    # Create agent
    agent = PunieAgent(model=model, name=name)

    # Create HTTP app
    app_instance = create_app()

    # Run dual protocol (stdio + HTTP)
    await run_dual(
        agent,
        app_instance,
        Host(host),
        Port(port),
        log_level,
    )
```

### Typer Command

```python
@app.command()
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="HTTP server bind address",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="HTTP server port",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Model name (overrides PUNIE_MODEL env var)",
    ),
    name: str = typer.Option(
        "punie-agent",
        "--name",
        help="Agent name for identification",
    ),
    log_dir: Path = typer.Option(
        Path("~/.punie/logs"),
        "--log-dir",
        help="Directory for log files",
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Logging level (debug, info, warning, error, critical)",
    ),
) -> None:
    """Run Punie agent with dual protocol support.

    Starts ACP agent over stdio (for PyCharm) and HTTP server (for testing).
    HTTP endpoints: /health, /echo
    """
    # Setup logging (file-only, never stdout)
    setup_logging(log_dir, log_level)

    # Resolve model from flag > env > default
    resolved_model = resolve_model(model)

    # Startup message (OK for serve command before agent starts)
    typer.echo("Starting Punie agent (dual protocol mode)")
    typer.echo(f"  Model: {resolved_model}")
    typer.echo(f"  HTTP: http://{host}:{port}")
    typer.echo(f"  Logs: {log_dir.expanduser() / 'punie.log'}")
    typer.echo("")

    # Run agent
    asyncio.run(run_serve_agent(resolved_model, name, host, port, log_level))
```

## Example File

**`examples/13_serve_dual.py`:**

```python
"""Example: Dual-protocol serve mode.

Demonstrates how `punie serve` runs both ACP stdio and HTTP
protocols concurrently for development and testing.
"""

import asyncio

from punie.agent import PunieAgent
from punie.http.app import create_app
from punie.http.runner import run_dual
from punie.http.types import Host, Port


async def main():
    print("=== Creating agent and HTTP app ===")
    agent = PunieAgent(model="test", name="dual-agent")
    app = create_app()

    print("\n=== Starting dual protocol mode ===")
    print("ACP stdio: Ready for PyCharm connection")
    print("HTTP: http://127.0.0.1:8000")
    print("Endpoints: /health, /echo")

    # In real usage, this runs until interrupted
    # For demo, we just show the setup
    print("\n(In production: await run_dual(agent, app, Host('127.0.0.1'), Port(8000), 'info'))")


if __name__ == "__main__":
    asyncio.run(main())
```

## Manual Testing

```bash
# Basic serve
uv run punie serve

# Custom host/port
uv run punie serve --host 0.0.0.0 --port 9000

# With model flag
uv run punie serve --model claude-sonnet-4-5-20250929

# Help text
uv run punie serve --help

# Main help shows subcommands
uv run punie --help

# Test HTTP endpoints (while serve is running)
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/echo -H "Content-Type: application/json" -d '{"message":"test"}'
```

## Files Modified

- `src/punie/cli.py` — add 1 async helper + 1 command
- `tests/test_cli.py` — add 6 tests
- `examples/13_serve_dual.py` — new example

## Dependencies

None — reuses existing punie.http infrastructure
