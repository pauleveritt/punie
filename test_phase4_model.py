#!/usr/bin/env python3
"""Test Phase 4 model with domain-specific queries."""

import asyncio
import os
from pathlib import Path

from punie.agent.factory import create_local_agent
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker


async def test_model(query: str) -> tuple[str, int]:
    """Test model with a query, return (output, num_messages)."""
    # Setup environment for local MLX server
    os.environ["OPENAI_API_KEY"] = "dummy"
    os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:8080/v1"

    model = "openai:mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
    workspace = Path.cwd()

    # Create agent
    agent, client = create_local_agent(model=model, workspace=workspace)

    deps = ACPDeps(
        client_conn=client,
        session_id="phase4-test",
        tracker=ToolCallTracker(),
    )

    # Run query
    result = await agent.run(query, deps=deps)

    # Count tool calls by checking message history
    # Agent's message history contains all turns
    num_turns = len(result.all_messages()) if hasattr(result, 'all_messages') else 0

    return result.output, num_turns


async def main():
    """Run test queries."""
    print("=" * 80)
    print("Phase 4 Model Testing")
    print("=" * 80)

    tests = [
        ("Find all classes that inherit from Protocol", "Should call grep/search tool"),
        ("What is dependency injection?", "Should answer directly without tools"),
        ("Show me examples of using Inject", "Should call read_file or grep"),
    ]

    for query, expectation in tests:
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"Expected: {expectation}")
        print(f"{'=' * 80}")

        try:
            output, turns = await test_model(query)

            # Show first 300 chars of output
            display_output = output[:300]
            if len(output) > 300:
                display_output += f"... ({len(output)} total chars)"

            print(f"\nOutput:\n{display_output}")
            print(f"\nMessage turns: {turns}")

            # Check for infinite loop
            if turns > 20:
                print("❌ FAILED: Too many turns (possible infinite loop)")
            elif output and turns > 0:
                print("✅ SUCCESS: Model responded appropriately")
            else:
                print("⚠️  UNCLEAR: Unusual response pattern")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("Testing complete!")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(main())
