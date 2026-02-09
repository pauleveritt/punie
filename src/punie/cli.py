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
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent import PunieAgent
from punie.agent.deps import ACPDeps
from punie.agent.factory import create_local_agent
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


def resolve_mode(mode_flag: str | None) -> str:
    """Resolve mode from CLI flag, env var, or default.

    Priority: CLI flag > PUNIE_MODE env var > "acp" default.
    """
    if mode_flag:
        return mode_flag
    return os.getenv("PUNIE_MODE", "acp")


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

    # Clear existing handlers to prevent duplicates
    root_logger.handlers.clear()

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
    logger = logging.getLogger(__name__)
    try:
        logger.info("=== run_acp_agent() starting ===")
        logger.info(f"Model: {model}")
        logger.info(f"Name: {name}")

        logger.info("Creating PunieAgent instance...")
        agent = PunieAgent(model=model, name=name)
        logger.info("PunieAgent created successfully")

        logger.info("Starting ACP agent via run_agent()...")
        await run_agent(agent)
        logger.info("=== run_acp_agent() complete ===")
    except Exception as exc:
        logger.exception("CRITICAL: run_acp_agent() failed")
        logger.error(f"Exception type: {type(exc).__name__}")
        logger.error(f"Exception message: {str(exc)}")
        raise


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
        "local",
        "--model",
        help="Model to use (default: local for offline development, or test/claude-sonnet-4-5-20250929)",
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

    By default, sets PUNIE_MODEL=local for offline development with MLX models.
    Use --model to specify test or a cloud model like claude-sonnet-4-5-20250929.
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
    list_models: bool = typer.Option(
        False,
        "--list",
        help="List recommended models",
    ),
) -> None:
    """Download MLX models for local inference.

    Downloads quantized MLX models from HuggingFace for offline development.
    Models are cached in ~/.cache/huggingface/hub/ (HuggingFace standard location).

    Recommended models:
    - mlx-community/Qwen2.5-Coder-7B-Instruct-4bit (~4GB, best balance)
    - mlx-community/Qwen2.5-Coder-3B-Instruct-4bit (~2GB, faster)
    - mlx-community/Qwen2.5-Coder-14B-Instruct-4bit (~8GB, highest quality)
    """
    # Handle --list flag
    if list_models:
        typer.echo("Available models:\n")
        typer.echo(
            "Name                                                  Size    Description"
        )
        typer.echo("─" * 80)
        typer.echo(
            "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit      ~15GB   Default (tool calling works!)"
        )
        typer.echo("")
        typer.echo("Note: Qwen2.5-Coder models don't support tool calling reliably.")
        typer.echo("      Use Qwen3-Coder for tool calling, or cloud models for best results.")
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

    # Download model to HuggingFace cache (default location)
    typer.echo(f"Downloading {model_name}...")
    typer.echo("Cache: ~/.cache/huggingface/hub/")
    typer.echo("")

    try:
        # Download to HuggingFace cache (no local_dir = uses default cache)
        cache_path = snapshot_download(repo_id=model_name)

        typer.secho("✓ Model downloaded successfully!", fg=typer.colors.GREEN)
        typer.echo(f"  Location: {cache_path}")
        typer.echo(f"\nUse with: punie serve --model local:{model_name}")
        typer.echo(f"Or test with: punie test-tools --model local:{model_name}")
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


async def _test_tool_calling(model: str, prompt: str, workspace: Path) -> bool:
    """Test if a model can properly format tool calls.

    Args:
        model: Model name (e.g., "local", "local:model-name", "test")
        prompt: Test prompt to send to the model
        workspace: Workspace directory for file operations

    Returns:
        True if tool calls were detected, False otherwise
    """
    typer.echo(f"\n{'='*80}")
    typer.secho("Testing Tool Calling", fg=typer.colors.BRIGHT_CYAN, bold=True)
    typer.echo(f"{'='*80}")
    typer.echo(f"Model: {model}")
    typer.echo(f"Workspace: {workspace}")
    typer.echo(f"Prompt: {prompt}")
    typer.echo(f"{'='*80}\n")

    # Create agent and client
    typer.echo("Creating agent...")
    agent, client = create_local_agent(model=model, workspace=workspace)

    # Create dependencies
    deps = ACPDeps(
        client_conn=client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    # Run the agent
    typer.echo("\nSending prompt to agent...\n")
    try:
        result = await agent.run(prompt, deps=deps)

        typer.echo(f"\n{'='*80}")
        typer.secho("RESULT", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.echo(f"{'='*80}")
        typer.echo(result.output)
        typer.echo(f"{'='*80}\n")

        # Show tool calls if any
        tool_calls_made = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            tool_calls_made.append(
                                f"{part.tool_name}({getattr(part, 'args', {})})"
                            )

        if tool_calls_made:
            typer.secho(
                "✓ SUCCESS - Tool calls were made:",
                fg=typer.colors.GREEN,
                bold=True,
            )
            for tc in tool_calls_made:
                typer.echo(f"  - {tc}")
            return True
        else:
            typer.secho(
                "✗ FAILED - No tool calls detected in response",
                fg=typer.colors.RED,
                bold=True,
            )
            typer.echo("\nThis usually means:")
            typer.echo("  1. The model doesn't support tool calling")
            typer.echo("  2. The model is outputting raw JSON instead of <tool_call> tags")
            typer.echo("  3. The quantization level is too aggressive")
            typer.echo("\nTry:")
            typer.echo("  - Using an 8-bit model instead of 4-bit")
            typer.echo("  - Using a larger model (14B instead of 7B)")
            typer.echo("  - Checking logs with --debug flag")
            return False

    except Exception as e:
        typer.secho(f"\n✗ ERROR: {e}", fg=typer.colors.RED, err=True)
        import traceback

        traceback.print_exc()
        return False


@app.command("ask")
def ask(
    prompt: str = typer.Argument(..., help="Question or instruction for the agent"),
    model: str = typer.Option(
        "local",
        "--model",
        help="Model to use (e.g., 'local', 'openai:gpt-4o', 'anthropic:claude-3-5-sonnet')",
    ),
    workspace: Path = typer.Option(
        Path.cwd(),
        "--workspace",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Workspace directory",
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Ask the agent a question and get a response (without PyCharm).

    Examples:
        punie ask "How many Python files are in this project?"
        punie ask "List all TODO comments" --model openai:gpt-4o
        punie ask "What does main.py do?" --workspace /path/to/project
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    asyncio.run(_run_ask(prompt, model, workspace))


async def _run_ask(prompt: str, model: str, workspace: Path) -> None:
    """Run a simple ask interaction."""
    from punie.agent.factory import create_local_agent
    from punie.agent.deps import ACPDeps
    from punie.acp.contrib.tool_calls import ToolCallTracker

    # Create agent and client
    agent, client = create_local_agent(model=model, workspace=workspace)

    # Create dependencies
    deps = ACPDeps(
        client_conn=client,
        session_id="ask-session",
        tracker=ToolCallTracker(),
    )

    # Run the agent
    try:
        result = await agent.run(prompt, deps=deps)

        # Show the response
        typer.echo(result.output)

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("test-tools")
def test_tools(
    model: str = typer.Option(
        "local",
        "--model",
        help="Model to test (e.g., 'local', 'local:model-name', 'test')",
    ),
    prompt: str = typer.Option(
        "How many Python files are in the current directory?",
        "--prompt",
        help="Test prompt to send",
    ),
    workspace: Path = typer.Option(
        Path.cwd(),
        "--workspace",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Workspace directory for file operations",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable DEBUG logging to see full prompts and outputs",
    ),
) -> None:
    """Test if a model can properly call tools without PyCharm.

    Tests tool calling locally to diagnose model issues. Useful for comparing
    models and verifying that tool calling works before using with PyCharm.
    """
    # Setup logging
    if debug:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        logging.getLogger("punie.models.mlx").setLevel(logging.DEBUG)

        # Add console handler for debug mode
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(console_handler)

    # Run test
    success = asyncio.run(_test_tool_calling(model, prompt, workspace))

    # Exit with appropriate code
    if not success:
        raise typer.Exit(1)


@app.command("stop-all")
def stop_all(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force kill processes (SIGKILL) if graceful shutdown fails",
    ),
    timeout: int = typer.Option(
        5,
        "--timeout",
        "-t",
        help="Seconds to wait for graceful shutdown before force kill",
    ),
) -> None:
    """Stop all running Punie agent processes.

    Finds all Punie processes and terminates them gracefully (SIGTERM).
    Use --force to send SIGKILL if processes don't stop within timeout.

    Cross-platform: Works on Linux, macOS, and Windows.
    """
    import psutil

    # Find all Punie processes
    punie_processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and any("punie" in arg.lower() for arg in cmdline):
                # Skip the current stop-all command process
                if "stop-all" not in " ".join(cmdline):
                    punie_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not punie_processes:
        typer.echo("No Punie processes found.")
        return

    typer.echo(f"Found {len(punie_processes)} Punie process(es):")
    for proc in punie_processes:
        try:
            cmdline = " ".join(proc.cmdline())
            typer.echo(f"  PID {proc.pid}: {cmdline[:80]}...")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Terminate processes gracefully
    typer.echo("\nTerminating processes gracefully (SIGTERM)...")
    for proc in punie_processes:
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            typer.secho(
                f"  Warning: Could not terminate PID {proc.pid}: {e}",
                fg=typer.colors.YELLOW,
            )

    # Wait for processes to exit
    gone, alive = psutil.wait_procs(punie_processes, timeout=timeout)

    # Report results
    if gone:
        typer.secho(
            f"\n✓ Stopped {len(gone)} process(es) successfully",
            fg=typer.colors.GREEN,
        )

    if alive:
        if force:
            typer.echo(f"\n{len(alive)} process(es) did not stop. Force killing...")
            for proc in alive:
                try:
                    proc.kill()
                    typer.secho(f"  Killed PID {proc.pid}", fg=typer.colors.YELLOW)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    typer.secho(
                        f"  Failed to kill PID {proc.pid}: {e}",
                        fg=typer.colors.RED,
                        err=True,
                    )
        else:
            typer.secho(
                f"\n⚠ {len(alive)} process(es) did not stop within {timeout}s",
                fg=typer.colors.YELLOW,
            )
            typer.echo("Use --force to force kill them:")
            for proc in alive:
                try:
                    typer.echo(f"  PID {proc.pid}")
                except psutil.NoSuchProcess:
                    continue
