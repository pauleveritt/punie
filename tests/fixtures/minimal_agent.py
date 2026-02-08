"""Minimal ACP agent for stdio integration testing.

This agent implements the bare minimum ACP protocol to test stdio connections.
It can be spawned as a subprocess and communicated with via stdin/stdout.

Now uses PunieAgent with Pydantic AI instead of hand-rolled MinimalAgent.
"""

import asyncio

from punie.acp import Agent, run_agent
from punie.agent import PunieAgent, create_pydantic_agent


async def main() -> None:
    """Run the minimal agent over stdio."""
    # Create Pydantic AI agent with TestModel (no real LLM)
    pydantic_agent = create_pydantic_agent(model="test")

    # Wrap in PunieAgent adapter for ACP protocol
    agent: Agent = PunieAgent(pydantic_agent, name="minimal-test-agent")

    # Run over stdio
    await run_agent(agent)


if __name__ == "__main__":
    asyncio.run(main())
