#!/usr/bin/env python3
"""Launch Toad with WebSocket agent.

This script launches Toad UI using the WebSocket-enabled agent subclass,
connecting to Punie server instead of spawning subprocess agents.

Usage:
    python scripts/run_toad_websocket.py [--server-url ws://localhost:8000/ws]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

logger = logging.getLogger(__name__)
app = typer.Typer()


def get_websocket_toad_agent_class(
    server_url: str = "ws://localhost:8000/ws",
    capture: object = None,
) -> type:
    """Get WebSocketToadAgent class.

    Delegates to punie.toad.agent.create_websocket_agent_class().
    Kept here for backward compatibility with tests that import this function.

    Args:
        server_url: Default WebSocket server URL
        capture: Optional ToadCapture for diagnostic logging

    Returns:
        WebSocketToadAgent class ready for instantiation
    """
    from punie.toad.agent import create_websocket_agent_class
    return create_websocket_agent_class(server_url, capture=capture)


@app.command()
def main(
    server_url: str = "ws://localhost:8000/ws",
    project: Path | None = None,
) -> None:
    """Launch Toad with WebSocket connection to Punie server.

    Always writes a diagnostic log to ~/.punie/logs/toad-debug.jsonl on exit
    recording every message and phase milestone. Useful for debugging
    "Initializing..." hangs: the last "phase" entry shows where it got stuck.

    Args:
        server_url: Punie server WebSocket URL
        project: Project root directory (defaults to current directory)
    """
    logging.basicConfig(level=logging.INFO)

    # Get project root
    if project is None:
        project = Path.cwd()

    logger.info(f"Starting Toad with WebSocket connection to {server_url} (project={project})")

    # Start diagnostic capture — records everything until the finally block writes it
    from punie.toad.diagnostic import ToadCapture
    capture = ToadCapture()
    capture.start(server_url)

    # Import Toad first (let it fully initialize)
    import toad.cli

    # CRITICAL: Import widgets.conversation BEFORE acp.agent to break circular import
    # (toad.acp.agent → toad.acp.messages → toad.acp.agent.Mode)
    import toad.widgets.conversation  # noqa: F401
    import toad.acp.agent

    # Get WebSocketToadAgent class from factory (handles all imports safely)
    WebSocketToadAgent = get_websocket_toad_agent_class(server_url, capture=capture)

    # Replace the Agent class (monkey-patch required — no upstream hook exists)
    toad.acp.agent.Agent = WebSocketToadAgent  # type: ignore[assignment]

    # Run Toad CLI with Punie agent auto-selected
    _exit_code = 0
    try:
        # Pass arguments to auto-select Punie agent and set project directory
        sys.argv = ["toad", "run", str(project), "-a", "punie"]
        toad.cli.main()
    except KeyboardInterrupt:
        print("\n\n✓ Toad closed")
    except Exception as exc:
        capture.on_error("toad_main", exc)
        print(f"\n❌ Error: {exc}", file=sys.stderr)
        _exit_code = 1
    finally:
        log_path = capture.write()
        print(f"[Toad diagnostic log: {log_path}]", file=sys.stderr)

    if _exit_code:
        sys.exit(_exit_code)


if __name__ == "__main__":
    app()
