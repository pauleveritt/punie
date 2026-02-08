"""Example: CLI utility usage.

Demonstrates model resolution and logging setup programmatically.
These utilities can be used outside the CLI context.

Usage:
    uv run python examples/11_cli_usage.py
"""

import logging
import os
from pathlib import Path

from punie.cli import resolve_model, setup_logging


def demonstrate_model_resolution():
    """Show how resolve_model() prioritizes CLI flag > env var > default."""
    print("=== Model Resolution Examples ===")

    # Priority 1: CLI flag
    model = resolve_model("claude-3-5-sonnet")
    print(f"With flag: {model}")  # claude-3-5-sonnet

    # Priority 2: PUNIE_MODEL env var
    os.environ["PUNIE_MODEL"] = "claude-3-opus"
    model = resolve_model(None)
    print(f"From env var: {model}")  # claude-3-opus

    # Priority 3: Default
    del os.environ["PUNIE_MODEL"]
    model = resolve_model(None)
    print(f"Default: {model}")  # test


def demonstrate_logging_setup():
    """Show how setup_logging() configures file-only logging."""
    print("\n=== Logging Setup Example ===")

    # Setup logging to example directory
    log_dir = Path.home() / ".punie" / "logs"
    setup_logging(log_dir, "debug")

    # Get logger and test it
    logger = logging.getLogger(__name__)
    logger.info("This message goes to file, not stdout")
    logger.debug("Debug messages are visible at debug level")

    print(f"Logs written to: {log_dir / 'punie.log'}")
    print("(stdout is reserved for ACP JSON-RPC, so logs go to files)")

    # Show root logger configuration
    root = logging.getLogger()
    print(f"\nRoot logger level: {logging.getLevelName(root.level)}")
    print(f"Handlers: {len(root.handlers)}")
    for handler in root.handlers:
        print(f"  - {handler.__class__.__name__}")


if __name__ == "__main__":
    demonstrate_model_resolution()
    demonstrate_logging_setup()

    print("\n=== Key Points ===")
    print("1. resolve_model() prioritizes: CLI flag > env > default")
    print("2. setup_logging() writes to files only (stdout is ACP JSON-RPC)")
    print("3. RotatingFileHandler keeps logs at ~10MB with 3 backups")
    print("4. stderr handler at CRITICAL level for startup failures")
