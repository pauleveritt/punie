"""Example: Enhanced test model with better debugging.

Demonstrates the enhanced test model that returns realistic responses
instead of just "a", making it easier to debug agent behavior.

Key features:
- Returns helpful text: "I understand the request. Let me help with that task."
- Does NOT call tools (configured with call_tools=None)
- Prevents deadlock in ACP request-response cycle
- Provides detailed logging for debugging
"""

import asyncio
import logging

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent import create_pydantic_agent
from punie.agent.deps import ACPDeps
from punie.testing import FakeClient

# Set up logging to see all the debug output
logging.basicConfig(
    level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s"
)


async def main():
    print("=== Enhanced Test Model Demo ===\n")

    # Create agent with "test" model - now returns helpful responses
    agent = create_pydantic_agent(model="test")

    # Create fake client for testing
    fake_client = FakeClient()

    # Set up dependencies
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    print("Running agent with test model...")
    print("(Check the logs above to see detailed execution traces)\n")

    # Run the agent
    result = await agent.run("Please help me understand this code", deps=deps)

    print(f"Agent response: {result.output}")
    print("\nNotice the response is helpful, not just 'a'!")


if __name__ == "__main__":
    asyncio.run(main())
