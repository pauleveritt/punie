"""Typer-based CLI for Punie.

Critical constraint: stdout is reserved for ACP JSON-RPC. All logging
goes to files (~/.punie/logs/punie.log). Version info prints to stderr.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import typer

from punie import __version__
from punie.acp import run_agent
from punie.agent import PunieAgent
from punie.http.app import create_app
from punie.http.runner import run_dual
from punie.http.types import Host, Port

app = typer.Typer(
    name="punie",
    help="AI coding agent that delegates tool execution to PyCharm via ACP",
    add_completion=False,
)


def resolve_punie_command() -> tuple[str, list[str]]:
    """Detect how to invoke Punie executable.

    Returns:
        (command, args) tuple:
        - If punie on PATH: ("/path/to/punie", [])
        - Otherwise: ("uvx", ["punie"])
    """
    punie_path = shutil.which("punie")
    if punie_path:
        return (punie_path, [])
    return ("uvx", ["punie"])


def generate_acp_config(
    command: str,
    args: list[str],
    env: dict[str, str],
) -> dict:
    """Generate JetBrains ACP configuration for Punie.

    Args:
        command: Executable path or "uvx"
        args: Arguments list (e.g., ["punie"] for uvx)
        env: Environment variables dict

    Returns:
        Complete acp.json structure
    """
    return {
        "default_mcp_settings": {
            "use_idea_mcp": True,
            "use_custom_mcp": True,
        },
        "agent_servers": {
            "punie": {
                "command": command,
                "args": args,
                "env": env,
            }
        },
    }


def merge_acp_config(existing: dict, punie_config: dict) -> dict:
    """Merge Punie config into existing ACP config.

    Preserves other agents and settings. Does not mutate inputs.

    Args:
        existing: Current acp.json content
        punie_config: New Punie configuration

    Returns:
        Merged configuration dict
    """
    import copy

    merged = copy.deepcopy(existing)

    # Ensure agent_servers exists
    if "agent_servers" not in merged:
        merged["agent_servers"] = {}

    # Update/add punie entry
    merged["agent_servers"]["punie"] = punie_config["agent_servers"]["punie"]

    # Add default_mcp_settings if missing
    if "default_mcp_settings" not in merged:
        merged["default_mcp_settings"] = punie_config["default_mcp_settings"]

    return merged


def resolve_model(model_flag: str | None) -> str:
    """Resolve model name from CLI flag, env var, or default.

    Priority: CLI flag > PUNIE_MODEL env var > "test" default.
    """
    if model_flag:
        return model_flag
    return os.getenv("PUNIE_MODEL", "test")


def setup_logging(log_dir: Path, log_level: str) -> None:
    """Configure file-only logging with RotatingFileHandler.

    Args:
        log_dir: Directory for log files (created if missing)
        log_level: Logging level (info, debug, warning, error, critical)
    """
    # Create log directory
    log_dir = log_dir.expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # File handler with rotation (10MB max, 3 backups)
    log_file = log_dir / "punie.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        ),
    )
    root_logger.addHandler(file_handler)

    # Stderr handler for critical errors only (not stdout — ACP owns it)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.CRITICAL)
    stderr_handler.setFormatter(
        logging.Formatter("%(levelname)s: %(message)s"),
    )
    root_logger.addHandler(stderr_handler)


async def run_acp_agent(model: str, name: str) -> None:
    """Create and run ACP agent.

    Args:
        model: Model name for agent
        name: Agent name for identification
    """
    agent = PunieAgent(model=model, name=name)
    await run_agent(agent)


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
        host=Host(host),
        port=Port(port),
        log_level=log_level,
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
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
    version: bool = typer.Option(
        False,
        "--version",
        help="Print version and exit",
    ),
) -> None:
    """Run Punie ACP agent via stdio transport.

    The agent communicates with PyCharm over stdin/stdout using the Agent
    Communication Protocol (ACP). All logging goes to files in ~/.punie/logs/
    to avoid corrupting the JSON-RPC protocol on stdout.
    """
    # Handle --version flag (prints to stderr, not stdout)
    if version:
        typer.echo(f"punie {__version__}", err=True)
        raise typer.Exit(0)

    # If invoked with a subcommand, let Typer handle it
    if ctx.invoked_subcommand is not None:
        return

    # Setup logging (file-only, never stdout)
    setup_logging(log_dir, log_level)

    # Resolve model from flag > env > default
    resolved_model = resolve_model(model)

    # Run ACP agent
    asyncio.run(run_acp_agent(resolved_model, name))


@app.command()
def init(
    model: str | None = typer.Option(
        None,
        "--model",
        help="Pre-configure PUNIE_MODEL environment variable",
    ),
    output: Path = typer.Option(
        Path.home() / ".jetbrains" / "acp.json",
        "--output",
        help="Output path for acp.json",
    ),
) -> None:
    """Generate JetBrains ACP configuration for Punie.

    Creates ~/.jetbrains/acp.json to enable PyCharm agent discovery.
    Merges with existing config to preserve other agents.
    """
    # Resolve Punie executable
    command, args = resolve_punie_command()

    # Build environment
    env = {}
    if model:
        env["PUNIE_MODEL"] = model

    # Generate base config
    punie_config = generate_acp_config(command, args, env)

    # Merge with existing if present
    if output.exists():
        try:
            existing = json.loads(output.read_text())
            final_config = merge_acp_config(existing, punie_config)
        except json.JSONDecodeError, KeyError:
            typer.secho(
                f"Warning: Could not parse existing {output}, overwriting",
                fg=typer.colors.YELLOW,
            )
            final_config = punie_config
    else:
        final_config = punie_config

    # Write config
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(final_config, indent=2) + "\n")

    # User feedback
    typer.secho(f"✓ Created {output}", fg=typer.colors.GREEN)
    typer.echo(f"  Command: {command}")
    if args:
        typer.echo(f"  Args: {' '.join(args)}")
    if env:
        for key, value in env.items():
            typer.echo(f"  {key}: {value}")


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
