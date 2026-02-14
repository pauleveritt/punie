#!/usr/bin/env python3
"""Test 1.5B model on real codebase question and measure performance."""

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
    """Test 1.5B model on Protocol subclass search."""
    print("=" * 80)
    print("TEST: Which classes in this codebase subclass from Protocol?")
    print("=" * 80)

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8766,
    )

    # Start server
    print("\nStarting MLX server...")
    server_start = time.perf_counter()
    server = ServerProcess(config=server_config)
    await server.start()
    server_time = time.perf_counter() - server_start
    print(f"Server started in {server_time:.2f} seconds")

    try:
        # Create agent
        print("Creating agent...")
        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)

        client = LocalClient(workspace=workspace)

        # Warm up the model first
        print("\n" + "=" * 80)
        print("WARMUP: Running simple query to load model...")
        print("=" * 80)
        warmup_tracker = ToolCallTracker()
        warmup_deps = ACPDeps(
            client_conn=client,
            session_id="warmup",
            tracker=warmup_tracker,
        )

        warmup_start = time.perf_counter()
        warmup_result = await agent.run("What is 2+2?", deps=warmup_deps)
        warmup_time = time.perf_counter() - warmup_start
        print(f"Warmup complete in {warmup_time:.2f}s")
        print(f"Warmup response: {warmup_result.output}\n")

        # Now run the actual query (warm performance)
        tracker = ToolCallTracker()
        deps = ACPDeps(
            client_conn=client,
            session_id="protocol-search",
            tracker=tracker,
        )

        question = "Which classes in this codebase subclass from Protocol?"
        print("=" * 80)
        print(f"ACTUAL QUERY (WARM): {question}")
        print("=" * 80)
        print("\nRunning agent...\n")

        query_start = time.perf_counter()
        result = await agent.run(question, deps=deps)
        query_time = time.perf_counter() - query_start

        print("=" * 80)
        print("1.5B MODEL RESPONSE:")
        print("=" * 80)
        print(result.output)
        print("=" * 80)

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

        print(f"\n{'=' * 80}")
        print("PERFORMANCE METRICS:")
        print(f"{'=' * 80}")
        print(f"Server startup time: {server_time:.2f}s")
        print(f"Warmup time (first query): {warmup_time:.2f}s")
        print(f"Warm query time (measured): {query_time:.2f}s")
        print(f"Total time (including warmup): {server_time + warmup_time + query_time:.2f}s")
        print(f"\nTool calls made: {len(tool_calls)}")
        for i, call in enumerate(tool_calls, 1):
            print(f"  {i}. {call['tool']}")
            if 'path' in call['args']:
                print(f"     path: {call['args']['path']}")
            if 'command' in call['args']:
                print(f"     command: {call['args']['command']}")

        # Save results for comparison
        with open("/tmp/punie_1.5b_result.txt", "w") as f:
            f.write("=" * 80 + "\n")
            f.write("1.5B MODEL RESPONSE\n")
            f.write("=" * 80 + "\n")
            f.write(result.output + "\n\n")
            f.write("=" * 80 + "\n")
            f.write("PERFORMANCE METRICS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Warmup time (first query): {warmup_time:.2f}s\n")
            f.write(f"Warm query time (measured): {query_time:.2f}s\n")
            f.write(f"Tool calls: {len(tool_calls)}\n")
            for i, call in enumerate(tool_calls, 1):
                f.write(f"  {i}. {call['tool']}\n")

        print("\nResults saved to /tmp/punie_1.5b_result.txt")

    finally:
        print("\nStopping server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
