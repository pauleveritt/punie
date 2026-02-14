#!/usr/bin/env python3
"""Benchmark the Protocol query with actual timing."""

import asyncio
import os
import time
from pathlib import Path

from punie.agent.factory import create_local_agent
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker


async def benchmark_query(query: str, runs: int = 3) -> tuple[float, str]:
    """Run query multiple times and return average time."""
    # Setup
    os.environ["OPENAI_API_KEY"] = "dummy"
    os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:8080/v1"

    model = "openai:mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
    workspace = Path.cwd()

    agent, client = create_local_agent(model=model, workspace=workspace)

    times = []
    output = ""

    for i in range(runs):
        deps = ACPDeps(
            client_conn=client,
            session_id=f"benchmark-{i}",
            tracker=ToolCallTracker(),
        )

        start = time.time()
        result = await agent.run(query, deps=deps)
        elapsed = time.time() - start

        times.append(elapsed)
        if i == 0:  # Save first run output
            output = result.output

        print(f"  Run {i+1}: {elapsed:.2f}s")

    avg_time = sum(times) / len(times)
    return avg_time, output


async def main():
    """Run benchmark."""
    print("=" * 80)
    print("Phase 4 Protocol Query Benchmark")
    print("=" * 80)

    query = "Find all classes that inherit from Protocol in this codebase"

    print(f"\nQuery: {query}")
    print("\nRunning 3 warm runs...")

    avg_time, output = await benchmark_query(query, runs=3)

    print(f"\n{'=' * 80}")
    print(f"Average Time: {avg_time:.2f}s")
    print(f"{'=' * 80}")

    print(f"\nSample Output (first 300 chars):")
    print(output[:300])
    if len(output) > 300:
        print(f"... ({len(output)} total chars)")


if __name__ == "__main__":
    asyncio.run(main())
