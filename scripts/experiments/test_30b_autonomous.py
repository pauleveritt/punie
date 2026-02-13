#!/usr/bin/env python3
"""Test if 30B model uses tools autonomously."""

import asyncio
import time
from pathlib import Path

from punie.agent.factory import create_pydantic_agent, create_server_model
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.training.server_config import ServerConfig
from punie.training.server import ServerProcess
from punie.local import LocalClient


async def main():
    """Test 30B model on Protocol search without explicit instructions."""
    print("=" * 80)
    print("TEST: 30B Model Autonomous Tool Usage")
    print("=" * 80)

    model_path = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8080,
    )

    print("\nStarting MLX server (this will take a while for 30B)...")
    server_start = time.perf_counter()
    server = ServerProcess(config=server_config)
    await server.start()
    server_time = time.perf_counter() - server_start
    print(f"Server started in {server_time:.2f}s")

    try:
        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)

        client = LocalClient(workspace=workspace)

        # Warmup
        print("\nWarming up...")
        warmup_tracker = ToolCallTracker()
        warmup_deps = ACPDeps(client_conn=client, session_id="warmup", tracker=warmup_tracker)
        warmup_start = time.perf_counter()
        await agent.run("What is 2+2?", deps=warmup_deps)
        warmup_time = time.perf_counter() - warmup_start
        print(f"Warmup complete in {warmup_time:.2f}s")

        # Test with simple question (NO explicit instructions)
        tracker = ToolCallTracker()
        deps = ACPDeps(client_conn=client, session_id="protocol-search-30b", tracker=tracker)

        question = "Which classes in this codebase subclass from Protocol?"

        print(f"\nQuestion (NO explicit instructions):")
        print(question)
        print("\nRunning agent...\n")

        start = time.perf_counter()
        result = await agent.run(question, deps=deps)
        elapsed = time.perf_counter() - start

        # Collect tool calls
        tool_calls = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            args = getattr(part, "args", {})
                            tool_calls.append({
                                "tool": part.tool_name,
                                "args": args
                            })

        print("=" * 80)
        print("30B MODEL RESPONSE:")
        print("=" * 80)
        print(result.output)
        print("=" * 80)

        print(f"\n{'=' * 80}")
        print("PERFORMANCE METRICS:")
        print(f"{'=' * 80}")
        print(f"Server startup: {server_time:.2f}s")
        print(f"Warmup time: {warmup_time:.2f}s")
        print(f"Warm query time: {elapsed:.2f}s")
        print(f"\nTool calls made: {len(tool_calls)}")
        for i, call in enumerate(tool_calls, 1):
            print(f"  {i}. {call['tool']}")
            if 'path' in call['args']:
                print(f"     path: {call['args']['path']}")
            if 'command' in call['args']:
                print(f"     command: {call['args']['command']}")

        print(f"\n{'=' * 80}")
        print("CONCLUSION:")
        print(f"{'=' * 80}")
        if len(tool_calls) > 0:
            print("✅ 30B model DOES use tools autonomously!")
            print("   Larger model has better reasoning about when to use tools.")
        else:
            print("❌ 30B model does NOT use tools autonomously.")
            print("   Even larger models lack autonomous tool usage reasoning.")

        # Save for comparison
        with open("/tmp/30b_autonomous_test.txt", "w") as f:
            f.write(f"Question: {question}\n\n")
            f.write(f"Response:\n{result.output}\n\n")
            f.write(f"Tool calls: {len(tool_calls)}\n")
            for i, call in enumerate(tool_calls, 1):
                f.write(f"  {i}. {call['tool']}\n")

    finally:
        print("\nStopping server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
