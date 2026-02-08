"""Dual-protocol agent for integration testing.

This agent runs both ACP stdio and HTTP server concurrently, spawnable
as a subprocess for testing dual-protocol operation.
"""

import asyncio
import sys

from punie.acp import Agent
from punie.agent import PunieAgent, create_pydantic_agent
from punie.http import Port, create_app, run_dual


async def main() -> None:
    """Run the dual-protocol agent.

    Expects port number as first command-line argument.
    """
    if len(sys.argv) < 2:
        print("Usage: python -m tests.fixtures.dual_agent <port>", file=sys.stderr)
        sys.exit(1)

    port: Port = Port(int(sys.argv[1]))

    # Create Pydantic AI agent with TestModel
    pydantic_agent = create_pydantic_agent(model="test")
    # Wrap in PunieAgent adapter for ACP protocol
    agent: Agent = PunieAgent(pydantic_agent, name="minimal-test-agent")

    app = create_app()

    await run_dual(agent, app, port=port, log_level="error")


if __name__ == "__main__":
    asyncio.run(main())
