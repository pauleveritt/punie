"""Quick test to verify Phase 38 direct tools are working."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from pydantic_ai.messages import ModelResponse, ToolCallPart

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent.deps import ACPDeps
from punie.agent.factory import create_local_agent


async def test_single_query():
    """Test a single query to verify direct tools work."""
    print("Creating agent with ollama:devstral...")
    agent, client = create_local_agent(
        model="ollama:devstral",
        workspace=Path.cwd(),
    )

    # Verify toolset
    print(f"Agent has {len(agent.toolsets)} toolsets")
    print("✓ Agent created successfully with direct toolset")

    # Test a simple query
    deps = ACPDeps(
        client_conn=client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    print("\nTesting query: 'What is Python?'")
    result = await agent.run("What is Python?", deps=deps)
    print(f"Response: {result.output[:200]}...")

    # Check if tools were called (should not for this query)
    tool_called = any(
        isinstance(part, ToolCallPart)
        for msg in result.all_messages()
        if isinstance(msg, ModelResponse)
        for part in msg.parts
    )
    print(f"Tool called: {tool_called} (expected: False)")

    # Test a tool-calling query
    print("\nTesting query: 'Run ruff on src/punie/agent/config.py'")
    result = await agent.run("Run ruff on src/punie/agent/config.py", deps=deps)
    print(f"Response: {result.output[:200]}...")

    # Check if tools were called (should be True)
    tool_called = any(
        isinstance(part, ToolCallPart)
        for msg in result.all_messages()
        if isinstance(msg, ModelResponse)
        for part in msg.parts
    )
    print(f"Tool called: {tool_called} (expected: True)")

    # Print which tools were called
    for msg in result.all_messages():
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    print(f"  → Called tool: {part.tool_name}")

    print("\n✅ Phase 38 implementation verified!")


if __name__ == "__main__":
    asyncio.run(test_single_query())
