"""Dual-protocol agent for integration testing.

This agent runs both ACP stdio and HTTP server concurrently, spawnable
as a subprocess for testing dual-protocol operation.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from punie.http import Port, create_app, run_dual
from tests.fixtures.minimal_agent import MinimalAgent


async def main() -> None:
    """Run the dual-protocol agent.

    Expects port number as first command-line argument.
    """
    if len(sys.argv) < 2:
        print("Usage: python -m tests.fixtures.dual_agent <port>", file=sys.stderr)
        sys.exit(1)

    port = Port(int(sys.argv[1]))
    agent = MinimalAgent()
    app = create_app()

    await run_dual(agent, app, port=port, log_level="error")


if __name__ == "__main__":
    asyncio.run(main())
