#!/usr/bin/env python3
"""Quick test of POC-trained model to check if infinite loop is fixed."""

import asyncio
from pathlib import Path

from punie.agent.factory import create_local_agent
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker

async def test_poc_model():
    """Test if POC model avoids infinite loop."""
    print("=" * 80)
    print("Testing POC Model - Infinite Loop Fix")
    print("=" * 80)

    # Note: This uses the trained adapters in models/qwen25-7b-distilled/adapters
    # which were just trained with 4 examples that have REAL tool results

    # Start local MLX server first:
    # uv run python -m mlx_lm server \
    #     --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
    #     --adapter-path models/qwen25-7b-distilled/adapters \
    #     --port 8080

    # For local MLX server, we need to specify the model name
    # The factory will parse local:MODEL_NAME and use default base URL
    # OR we can directly create the model string
    workspace = Path.cwd()

    # Use openai: prefix with explicit base_url
    import os
    os.environ["OPENAI_API_KEY"] = "dummy"  # Required but not used
    os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:8080/v1"

    model = "openai:mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"

    print(f"\nModel: {model}")
    print(f"Base URL: http://127.0.0.1:8080/v1")
    print(f"Workspace: {workspace}")

    # Create agent
    agent, client = create_local_agent(
        model=model,
        workspace=workspace
    )

    # Test query: Should call grep once or twice, then give answer
    query = "Find all classes that inherit from Protocol in this codebase"

    print(f"\nQuery: {query}")
    print("\nRunning agent...\n")

    deps = ACPDeps(
        client_conn=client,
        session_id="poc-test",
        tracker=ToolCallTracker(),
    )

    try:
        result = await agent.run(query, deps=deps)

        print("=" * 80)
        print("RESULT")
        print("=" * 80)
        # Use .output attribute from AgentRunResult
        output_text = result.output[:500] if len(result.output) > 500 else result.output
        print(output_text)
        if len(result.output) > 500:
            print(f"... ({len(result.output)} total characters)")
        print()

        # Check tool calls
        tool_count = len(deps.tracker.tool_calls)
        print(f"\nTool calls made: {tool_count}")
        for i, call in enumerate(deps.tracker.tool_calls, 1):
            print(f"  {i}. {call.tool_name}")

        # Success criteria
        if 1 <= tool_count <= 3 and result.output:
            print("\n✅ SUCCESS - Model called tools and gave final answer!")
            print("   (No infinite loop!)")
            return True
        elif tool_count > 10:
            print(f"\n❌ FAILED - Model looped ({tool_count} calls)")
            return False
        else:
            print(f"\n⚠️  UNCLEAR - Unusual pattern ({tool_count} calls, answer: {bool(result.output)})")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("\nMake sure the 7B server is running with:")
    print("  uv run python -m mlx_lm server \\")
    print("      --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \\")
    print("      --adapter-path models/qwen25-7b-distilled/adapters \\")
    print("      --port 8080")
    print("\nPress Enter when ready...")
    input()

    success = asyncio.run(test_poc_model())
    exit(0 if success else 1)
