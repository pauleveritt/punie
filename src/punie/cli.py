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


def resolve_perf(perf_flag: bool) -> bool:
    """Resolve performance reporting from CLI flag or env var.

    Priority: CLI flag > PUNIE_PERF env var > False default.
    Set PUNIE_PERF=1 in acp.json to enable performance reporting.
    """
    if perf_flag:
        return True
    return os.getenv("PUNIE_PERF", "0") == "1"


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
    asyncio.run(run_acp_agent(resolved_model, name))


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

    By default, sets PUNIE_MODEL=local for local development with LM Studio.
    Use --model to specify test or a cloud model like claude-sonnet-4-5-20250929.

    For local models, start LM Studio (https://lmstudio.ai/) and load a model first.
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


async def _test_tool_calling(model: str, prompt: str, workspace: Path) -> bool:
    """Test if a model can properly format tool calls.

    Args:
        model: Model name (e.g., "local", "local:model-name", "test")
        prompt: Test prompt to send to the model
        workspace: Workspace directory for file operations

    Returns:
        True if tool calls were detected, False otherwise
    """
    from punie.training.tool_call_parser import parse_tool_calls

    typer.echo(f"\n{'=' * 80}")
    typer.secho("Testing Tool Calling", fg=typer.colors.BRIGHT_CYAN, bold=True)
    typer.echo(f"{'=' * 80}")
    typer.echo(f"Model: {model}")
    typer.echo(f"Workspace: {workspace}")
    typer.echo(f"Prompt: {prompt}")
    typer.echo(f"{'=' * 80}\n")

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

        typer.echo(f"\n{'=' * 80}")
        typer.secho("RESULT", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.echo(f"{'=' * 80}")
        typer.echo(result.output)
        typer.echo(f"{'=' * 80}\n")

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

        # Fallback: parse tool calls from raw text (for local models)
        if not tool_calls_made:
            _, parsed_calls = parse_tool_calls(result.output)
            tool_calls_made = [
                f"{call['name']}({call.get('arguments', {})})"
                for call in parsed_calls if "name" in call
            ]

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
            typer.echo(
                "  2. The model is outputting raw JSON instead of <tool_call> tags"
            )
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
    perf: bool = typer.Option(False, "--perf", help="Generate performance report"),
) -> None:
    """Ask the agent a question and get a response (without PyCharm).

    Examples:
        punie ask "How many Python files are in this project?"
        punie ask "List all TODO comments" --model openai:gpt-4o
        punie ask "What does main.py do?" --workspace /path/to/project
        punie ask "Count Python files" --perf  # Generate performance report
        punie ask "Explain the code" --model local:  # Use LM Studio

    For local models, start LM Studio (https://lmstudio.ai/) first and load a model.
    Performance reporting can also be enabled via PUNIE_PERF=1 environment variable.
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Resolve perf from flag or env var
    resolved_perf = resolve_perf(perf)

    asyncio.run(_run_ask(prompt, model, workspace, resolved_perf))


async def _run_ask(
    prompt: str,
    model: str,
    workspace: Path,
    perf: bool = False,
) -> None:
    """Run a simple ask interaction."""
    from datetime import datetime, timezone

    from punie.acp.contrib.tool_calls import ToolCallTracker
    from punie.agent.deps import ACPDeps
    from punie.agent.factory import create_local_agent
    from punie.perf import PerformanceCollector, generate_html_report

    # Create performance collector if requested
    collector = PerformanceCollector() if perf else None

    # Create agent and client (uses default config)
    agent, client = create_local_agent(
        model=model, workspace=workspace, perf_collector=collector
    )

    # Start prompt timing if collecting performance
    if collector:
        # Determine backend from model name
        backend = "local" if model.startswith("local") else "ide"
        collector.start_prompt(model, backend)

    # Create dependencies
    deps = ACPDeps(
        client_conn=client,
        session_id="ask-session",
        tracker=ToolCallTracker(),
    )

    # Run the agent
    try:
        result = await agent.run(prompt, deps=deps)

        # End prompt timing if collecting performance
        if collector:
            collector.end_prompt()

        # Show the response
        typer.echo(result.output)

        # Generate and save performance report if requested
        if collector:
            report_data = collector.report()
            html = generate_html_report(report_data)

            # Generate filename with timestamp
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            report_path = Path.cwd() / f"punie-perf-{timestamp}.html"

            report_path.write_text(html)
            typer.echo(f"\nPerformance report: {report_path}")

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
        except psutil.NoSuchProcess, psutil.AccessDenied:
            continue

    if not punie_processes:
        typer.echo("No Punie processes found.")
        return

    typer.echo(f"Found {len(punie_processes)} Punie process(es):")
    for proc in punie_processes:
        try:
            cmdline = " ".join(proc.cmdline())
            typer.echo(f"  PID {proc.pid}: {cmdline[:80]}...")
        except psutil.NoSuchProcess, psutil.AccessDenied:
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


# Training commands

@app.command("train")
def train(
    data_dir: Path = typer.Argument(
        ...,
        help="Directory with train.jsonl, valid.jsonl, test.jsonl files",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    model: str = typer.Option(
        "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        "--model",
        "-m",
        help="Base model to fine-tune",
    ),
    output: Path = typer.Option(
        Path("adapters/default"),
        "--output",
        "-o",
        help="Output directory for adapter weights",
    ),
    iters: int = typer.Option(
        100,
        "--iters",
        "-i",
        help="Number of training iterations",
    ),
    batch_size: int = typer.Option(
        2,
        "--batch-size",
        "-b",
        help="Training batch size",
    ),
    learning_rate: float = typer.Option(
        1e-5,
        "--learning-rate",
        "-lr",
        help="Learning rate",
    ),
) -> None:
    """Run LoRA fine-tuning on a dataset.

    Trains a LoRA adapter on the provided dataset and saves adapter weights.
    """
    from punie.training.lora_config import LoRAConfig
    from punie.training.train_runner import run_training

    typer.echo(f"🚀 Starting LoRA training")
    typer.echo(f"   Model: {model}")
    typer.echo(f"   Data: {data_dir}")
    typer.echo(f"   Output: {output}")
    typer.echo(f"   Iterations: {iters}")

    config = LoRAConfig(
        base_model=model,
        data_directory=data_dir,
        output_directory=output,
        num_iters=iters,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )

    try:
        adapter_path = asyncio.run(run_training(config))
        typer.secho(f"\n✅ Training complete!", fg=typer.colors.GREEN)
        typer.echo(f"   Adapter saved to: {adapter_path}")
    except Exception as e:
        typer.secho(f"\n❌ Training failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("eval")
def eval_model(
    model: str = typer.Option(
        "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        "--model",
        "-m",
        help="Model to evaluate",
    ),
    adapter: Path | None = typer.Option(
        None,
        "--adapter",
        "-a",
        help="Path to LoRA adapter weights (optional)",
    ),
    port: int = typer.Option(
        8080,
        "--port",
        "-p",
        help="Server port",
    ),
    no_server: bool = typer.Option(
        False,
        "--no-server",
        help="Don't manage server (use existing server)",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for HTML report (default: eval_TIMESTAMP.html)",
    ),
    workspace: Path = typer.Option(
        Path.cwd(),
        "--workspace",
        "-w",
        help="Workspace directory for file operations",
    ),
) -> None:
    """Evaluate a model against the baseline prompt suite.

    Runs the evaluation suite and generates an HTML report with scores.
    By default, starts and manages the mlx_lm server automatically.

    Examples:
      punie eval --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit
      punie eval --adapter adapters/my-adapter/
      punie eval --no-server --port 8080  # Use existing server
    """
    from datetime import datetime, timezone
    from punie.training.eval_suites import create_baseline_suite
    from punie.training.eval_runner import EvalRunConfig, run_evaluation
    from punie.training.eval_report import generate_eval_html_report
    from punie.training.server_config import ServerConfig

    typer.echo(f"🔍 Evaluating model")
    typer.echo(f"   Model: {model}")
    if adapter:
        typer.echo(f"   Adapter: {adapter}")
    typer.echo(f"   Port: {port}")
    if no_server:
        typer.echo(f"   Using existing server")
    typer.echo("")

    # Create server config
    server_config = ServerConfig(
        model_path=model,
        adapter_path=adapter,
        port=port,
    )

    # Get baseline suite
    suite = create_baseline_suite()

    # Create eval config
    eval_config = EvalRunConfig(
        server_config=server_config,
        suite=suite,
        workspace=workspace,
        manage_server=not no_server,
    )

    # Run evaluation
    try:
        report = asyncio.run(run_evaluation(eval_config))

        # Generate output path if not provided
        if output is None:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            output = Path.cwd() / f"eval_{timestamp}.html"

        # Generate HTML report
        html = generate_eval_html_report(report, suite)
        output.write_text(html)

        # Print summary
        typer.secho(f"\n✅ Evaluation complete!", fg=typer.colors.GREEN)
        typer.echo(f"\n📊 Results:")

        # Calculate average score
        total_score = sum(r.score for r in report.results)
        avg_score = total_score / max(len(report.results), 1)
        typer.echo(f"   Average score: {avg_score:.1%}")

        # Count successes
        successes = sum(1 for r in report.results if r.success)
        typer.echo(f"   Successful: {successes}/{len(report.results)}")

        # Show category breakdown
        from collections import defaultdict
        category_scores = defaultdict(list)
        for result in report.results:
            # Find matching prompt to get category
            for prompt in suite.prompts:
                if prompt.id == result.prompt_id:
                    category_scores[prompt.category].append(result.score)
                    break

        typer.echo(f"\n   By category:")
        for category, scores in sorted(category_scores.items()):
            avg = sum(scores) / max(len(scores), 1)
            typer.echo(f"     {category}: {avg:.1%}")

        typer.echo(f"\n   Report saved to: {output}")

    except Exception as e:
        typer.secho(f"\n❌ Evaluation failed: {e}", fg=typer.colors.RED, err=True)
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


dataset_app = typer.Typer(help="Dataset management commands")
app.add_typer(dataset_app, name="dataset")


@dataset_app.command("validate")
def dataset_validate(
    directory: Path = typer.Argument(
        ...,
        help="Directory with train.jsonl, valid.jsonl, test.jsonl files",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Validate a training dataset.

    Checks for common issues like invalid roles, empty content, etc.
    """
    from punie.training.dataset_io import read_dataset
    from punie.training.dataset_validation import validate_dataset

    typer.echo(f"📋 Validating dataset: {directory}")

    try:
        dataset = read_dataset(directory)
        errors = validate_dataset(dataset)

        if not errors:
            typer.secho("✅ Dataset is valid!", fg=typer.colors.GREEN)
            typer.echo(f"   Train: {len(dataset.train)} examples")
            typer.echo(f"   Valid: {len(dataset.valid)} examples")
            typer.echo(f"   Test: {len(dataset.test)} examples")
        else:
            typer.secho(f"\n❌ Found {len(errors)} validation errors:", fg=typer.colors.RED)
            for error in errors[:10]:  # Show first 10
                typer.echo(f"   • {error}")
            if len(errors) > 10:
                typer.echo(f"   ... and {len(errors) - 10} more")
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"❌ Validation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@dataset_app.command("stats")
def dataset_stats(
    directory: Path = typer.Argument(
        ...,
        help="Directory with train.jsonl, valid.jsonl, test.jsonl files",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Show statistics for a training dataset."""
    from punie.training.dataset_io import compute_stats, read_dataset

    typer.echo(f"📊 Dataset statistics: {directory}\n")

    try:
        dataset = read_dataset(directory)
        stats = compute_stats(dataset)

        typer.echo(f"Total examples: {stats.total_examples}")
        typer.echo(f"\nSplit breakdown:")
        typer.echo(f"  Train: {stats.train_count} ({stats.train_count / max(stats.total_examples, 1) * 100:.1f}%)")
        typer.echo(f"  Valid: {stats.valid_count} ({stats.valid_count / max(stats.total_examples, 1) * 100:.1f}%)")
        typer.echo(f"  Test:  {stats.test_count} ({stats.test_count / max(stats.total_examples, 1) * 100:.1f}%)")
        typer.echo(f"\nAverage messages per example: {stats.avg_messages_per_example:.1f}")

    except Exception as e:
        typer.secho(f"❌ Failed to compute stats: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@dataset_app.command("download")
def dataset_download(
    name: str = typer.Argument(
        ...,
        help="Dataset name (sample, python-code)",
    ),
    output: Path = typer.Option(
        Path("data/downloaded"),
        "--output",
        "-o",
        help="Output directory",
    ),
    max_examples: int = typer.Option(
        100,
        "--max",
        "-m",
        help="Maximum examples to download",
    ),
) -> None:
    """Download a dataset and convert to training format.

    Available datasets:
      sample      - Synthetic Python Q&A (for testing)
      python-code - Python code examples from CodeSearchNet
    """
    from punie.training.downloaders import download_python_code_dataset, download_sample_dataset

    downloaders = {
        "sample": download_sample_dataset,
        "python-code": download_python_code_dataset,
    }

    if name not in downloaders:
        typer.secho(f"❌ Unknown dataset: {name}", fg=typer.colors.RED, err=True)
        typer.echo(f"Available: {', '.join(downloaders.keys())}")
        raise typer.Exit(1)

    typer.echo(f"📥 Downloading dataset: {name}")
    typer.echo(f"   Output: {output}")
    typer.echo(f"   Max examples: {max_examples}")
    typer.echo("\nThis may take a moment...")

    try:
        stats = downloaders[name](output, max_examples=max_examples)

        typer.secho(f"\n✅ Download complete!", fg=typer.colors.GREEN)
        typer.echo(f"\n📊 Statistics:")
        typer.echo(f"   Total: {stats.total_examples} examples")
        typer.echo(f"   Train: {stats.train_count}")
        typer.echo(f"   Valid: {stats.valid_count}")
        typer.echo(f"   Test:  {stats.test_count}")
        typer.echo(f"   Avg messages: {stats.avg_messages_per_example:.1f}")
        typer.echo(f"\n💡 Next steps:")
        typer.echo(f"   Validate: punie dataset validate {output}")
        typer.echo(f"   Train:    punie train {output}")

    except Exception as e:
        typer.secho(f"\n❌ Download failed: {e}", fg=typer.colors.RED, err=True)
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@dataset_app.command("filter")
def dataset_filter(
    input_dir: Path = typer.Argument(
        ...,
        help="Input dataset directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output directory for filtered dataset",
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help="Filter by language (e.g., 'en')",
    ),
    min_python: str | None = typer.Option(
        None,
        "--min-python",
        help="Minimum Python version (e.g., '3', '3.10')",
    ),
    min_messages: int | None = typer.Option(
        None,
        "--min-messages",
        help="Minimum messages per example",
    ),
) -> None:
    """Filter a dataset by quality criteria.

    Apply one or more filters to remove low-quality examples. Each filter
    produces a report showing what was kept vs. removed.

    Examples:
      punie dataset filter data/raw/ -o data/step-a/ --language en
      punie dataset filter data/step-a/ -o data/step-b/ --min-python 3.10
    """
    from punie.training.dataset_filters import (
        filter_by_content_quality,
        filter_by_language,
        filter_by_python_version,
    )
    from punie.training.dataset_io import read_dataset, write_dataset
    from punie.training.dataset import TrainingDataset

    typer.echo(f"🔍 Filtering dataset: {input_dir}")
    typer.echo(f"   Output: {output_dir}\n")

    try:
        # Read input dataset
        dataset = read_dataset(input_dir)
        typer.echo(f"📊 Input: {len(dataset.train) + len(dataset.valid) + len(dataset.test)} examples\n")

        # Initialize kept sets (filters will update these)
        train_kept = dataset.train
        valid_kept = dataset.valid
        test_kept = dataset.test

        # Apply filters
        if language:
            typer.echo(f"🌍 Filtering by language: {language}")
            train_kept, train_rem = filter_by_language(train_kept, language)
            valid_kept, valid_rem = filter_by_language(valid_kept, language)
            test_kept, test_rem = filter_by_language(test_kept, language)
            removed = len(train_rem) + len(valid_rem) + len(test_rem)
            typer.echo(f"   Removed: {removed} examples")

        if min_python:
            typer.echo(f"🐍 Filtering by Python version: >={min_python}")
            train_kept, train_rem = filter_by_python_version(train_kept, min_python)
            valid_kept, valid_rem = filter_by_python_version(valid_kept, min_python)
            test_kept, test_rem = filter_by_python_version(test_kept, min_python)
            removed = len(train_rem) + len(valid_rem) + len(test_rem)
            typer.echo(f"   Removed: {removed} examples")

        if min_messages:
            typer.echo(f"💬 Filtering by message count: >={min_messages}")
            train_kept, train_rem = filter_by_content_quality(train_kept, min_messages)
            valid_kept, valid_rem = filter_by_content_quality(valid_kept, min_messages)
            test_kept, test_rem = filter_by_content_quality(test_kept, min_messages)
            removed = len(train_rem) + len(valid_rem) + len(test_rem)
            typer.echo(f"   Removed: {removed} examples")

        # Create filtered dataset
        filtered = TrainingDataset(
            name=dataset.name,
            version=f"{dataset.version}-filtered",
            train=train_kept,
            valid=valid_kept,
            test=test_kept,
        )

        # Write output
        write_dataset(filtered, output_dir)

        typer.secho(f"\n✅ Filtering complete!", fg=typer.colors.GREEN)
        typer.echo(f"\n📊 Output: {len(filtered.train) + len(filtered.valid) + len(filtered.test)} examples")
        typer.echo(f"   Train: {len(filtered.train)}")
        typer.echo(f"   Valid: {len(filtered.valid)}")
        typer.echo(f"   Test:  {len(filtered.test)}")

        original_total = len(dataset.train) + len(dataset.valid) + len(dataset.test)
        filtered_total = len(filtered.train) + len(filtered.valid) + len(filtered.test)
        retention = filtered_total / max(original_total, 1) * 100

        typer.echo(f"\n   Retention rate: {retention:.1f}%")

    except Exception as e:
        typer.secho(f"❌ Filtering failed: {e}", fg=typer.colors.RED, err=True)
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@dataset_app.command("merge")
def dataset_merge(
    input_dirs: list[Path] = typer.Argument(
        ...,
        help="Input dataset directories to merge",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output directory for merged dataset",
    ),
    name: str = typer.Option(
        "merged",
        "--name",
        "-n",
        help="Name for merged dataset",
    ),
) -> None:
    """Merge multiple datasets into one.

    Combines training examples from multiple sources. Useful for adding
    hand-authored examples to downloaded datasets.

    Example:
      punie dataset merge data/filtered/step-c/ data/hand-authored/ \\
          --output data/merged/v1/ --name combined-v1
    """
    from punie.training.dataset import TrainingDataset
    from punie.training.dataset_io import read_dataset, write_dataset

    typer.echo(f"🔀 Merging {len(input_dirs)} datasets")
    typer.echo(f"   Output: {output_dir}\n")

    try:
        # Read all datasets
        datasets = []
        total_examples = 0

        for input_dir in input_dirs:
            dataset = read_dataset(input_dir)
            count = len(dataset.train) + len(dataset.valid) + len(dataset.test)
            typer.echo(f"📁 {input_dir}: {count} examples")
            datasets.append(dataset)
            total_examples += count

        # Merge splits
        all_train = []
        all_valid = []
        all_test = []

        for dataset in datasets:
            all_train.extend(dataset.train)
            all_valid.extend(dataset.valid)
            all_test.extend(dataset.test)

        # Create merged dataset
        merged = TrainingDataset(
            name=name,
            version="1.0",
            train=tuple(all_train),
            valid=tuple(all_valid),
            test=tuple(all_test),
        )

        # Write output
        write_dataset(merged, output_dir)

        typer.secho(f"\n✅ Merge complete!", fg=typer.colors.GREEN)
        typer.echo(f"\n📊 Total: {total_examples} examples")
        typer.echo(f"   Train: {len(merged.train)}")
        typer.echo(f"   Valid: {len(merged.valid)}")
        typer.echo(f"   Test:  {len(merged.test)}")

    except Exception as e:
        typer.secho(f"❌ Merge failed: {e}", fg=typer.colors.RED, err=True)
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)
