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
    try:
        asyncio.run(run_acp_agent(resolved_model, name))
    except RuntimeError as e:
        if "not downloaded" in str(e):
            typer.secho(str(e), fg=typer.colors.RED, err=True)
            raise typer.Exit(1) from e
        raise


@app.command()
def init(
    model: str | None = typer.Option(
        "test",
        "--model",
        help="Model to use (default: test for debugging, or specify claude-sonnet-4-5-20250929)",
    ),
    output: Path = typer.Option(
        Path.home() / ".jetbrains" / "acp.json",
        "--output",
        help="Output path for acp.json",
    ),
    include_venv: bool = typer.Option(
        True,
        "--include-venv/--no-venv",
        help="Include UV_PROJECT_ENVIRONMENT for local development",
    ),
) -> None:
    """Generate JetBrains ACP configuration for Punie.

    Creates ~/.jetbrains/acp.json to enable PyCharm agent discovery.
    Merges with existing config to preserve other agents.

    By default, sets PUNIE_MODEL=test for easier debugging with enhanced logging.
    Use --model to specify a real model like claude-sonnet-4-5-20250929.
    """
    # Resolve Punie executable
    command, args = resolve_punie_command()

    # Build environment
    env = {}
    if model:
        env["PUNIE_MODEL"] = model

    # Add venv path if requested and we're in a uv project
    if include_venv:
        venv_path = os.getenv("VIRTUAL_ENV")
        if venv_path:
            env["UV_PROJECT_ENVIRONMENT"] = venv_path
            typer.echo(f"  Using venv: {venv_path}")

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
    if model == "test":
        typer.secho(
            f"  Model: {model} (enhanced test model with detailed logging)",
            fg=typer.colors.YELLOW,
        )
    elif model:
        typer.echo(f"  Model: {model}")
    if env:
        for key, value in env.items():
            if key != "PUNIE_MODEL":  # Already shown above
                typer.echo(f"  {key}: {value}")


@app.command("download-model")
def download_model(
    model_name: str = typer.Argument(
        "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        help="HuggingFace model name to download",
    ),
    models_dir: Path = typer.Option(
        Path("~/.cache/punie/models"),
        "--models-dir",
        help="Directory to store downloaded models (cached, re-downloadable)",
    ),
    list_models: bool = typer.Option(
        False,
        "--list",
        help="List recommended models",
    ),
) -> None:
    """Download MLX models for local inference.

    Downloads quantized MLX models from HuggingFace for offline development.
    Models are stored in ~/.punie/models/ by default.

    Recommended models:
    - mlx-community/Qwen2.5-Coder-7B-Instruct-4bit (~4GB, best balance)
    - mlx-community/Qwen2.5-Coder-3B-Instruct-4bit (~2GB, faster)
    - mlx-community/Qwen2.5-Coder-14B-Instruct-4bit (~8GB, highest quality)
    """
    # Handle --list flag
    if list_models:
        typer.echo("Available models:\n")
        typer.echo(
            "Name                                            Size    Description"
        )
        typer.echo("─" * 78)
        typer.echo(
            "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit   ~4GB    Default (best balance)"
        )
        typer.echo(
            "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit   ~2GB    Faster, simpler tasks"
        )
        typer.echo(
            "mlx-community/Qwen2.5-Coder-14B-Instruct-4bit  ~8GB    Highest quality"
        )
        typer.echo("\nDownload with: punie download-model <model-name>")
        raise typer.Exit(0)

    # Check if mlx-lm is installed
    try:
        from huggingface_hub import snapshot_download  # type: ignore[import-untyped]
    except ImportError as e:
        msg = (
            "Local model support requires mlx-lm.\n"
            "Install with: uv pip install 'punie[local]'"
        )
        typer.secho(msg, fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e

    # Expand models directory
    models_dir = models_dir.expanduser()
    models_dir.mkdir(parents=True, exist_ok=True)

    # Download model
    typer.echo(f"Downloading {model_name}...")
    typer.echo(f"Target directory: {models_dir}")
    typer.echo("")

    try:
        snapshot_download(
            repo_id=model_name,
            local_dir=models_dir / model_name.replace("/", "--"),
        )
        typer.secho("✓ Model downloaded successfully!", fg=typer.colors.GREEN)
        typer.echo(f"  Location: {models_dir / model_name.replace('/', '--')}")
        typer.echo(f"\nUse with: punie serve --model local:{model_name}")
    except Exception as e:
        typer.secho(f"Error downloading model: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e


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
    try:
        asyncio.run(run_serve_agent(resolved_model, name, host, port, log_level))
    except RuntimeError as e:
        if "not downloaded" in str(e):
            typer.secho(f"\nError: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1) from e
        raise
