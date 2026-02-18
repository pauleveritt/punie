#!/usr/bin/env python3
"""Quick test: Does max_tokens reduction speed up Devstral?"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.agent.factory import create_local_agent


async def test_query(max_tokens: int):
    """Test single query with given max_tokens."""
    print(f"\nTesting with max_tokens={max_tokens}")
    print("=" * 60)

    config = AgentConfig(
        instructions="You are a concise AI assistant. Always use tools directly without explanation.",
        max_tokens=max_tokens,
        temperature=0.0,
    )

    agent, client = create_local_agent(
        model="ollama:devstral",
        workspace=Path.cwd(),
        config=config,
    )

    deps = ACPDeps(
        client_conn=client,
        session_id="speed-test",
        tracker=ToolCallTracker(),
    )

    query = "Check for type errors in src/"

    start = time.time()
    result = await agent.run(query, deps=deps)
    elapsed = time.time() - start

    response = result.output
    response_len = len(response)

    print(f"Time: {elapsed:.2f}s")
    print(f"Response length: {response_len} chars")
    print(f"Response: {response[:200]}...")

    return elapsed, response_len


async def main():
    """Compare different max_tokens settings."""
    print("Devstral Speed Test: max_tokens Impact")
    print("=" * 60)

    results = []
    for max_tokens in [512, 1024, 2048]:
        try:
            elapsed, resp_len = await test_query(max_tokens)
            results.append((max_tokens, elapsed, resp_len))
        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'max_tokens':<12} {'Time (s)':<12} {'Response Len':<15} {'Speedup':<10}")
    print("-" * 60)

    baseline = results[0][1] if results else 0
    for max_tokens, elapsed, resp_len in results:
        speedup = f"{baseline/elapsed:.2f}x" if elapsed > 0 else "N/A"
        print(f"{max_tokens:<12} {elapsed:<12.2f} {resp_len:<15} {speedup:<10}")


if __name__ == "__main__":
    asyncio.run(main())
