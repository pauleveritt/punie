#!/usr/bin/env python3
"""Compare 7B distilled model performance vs baseline."""

import asyncio
import time
import psutil
from pathlib import Path
from punie.agent.factory import create_pydantic_agent
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.local import LocalClient

async def test_model(model_name: str, label: str):
    """Test a model with the protocols query."""
    print(f"\n{'=' * 80}")
    print(f"Testing: {label}")
    print(f"{'=' * 80}\n")

    # Record initial memory
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024 / 1024  # GB

    print(f"Creating agent...")
    agent_config = AgentConfig(temperature=0.0)
    agent = create_pydantic_agent(model=model_name, config=agent_config)

    client = LocalClient(workspace=Path.cwd())
    tracker = ToolCallTracker()
    deps = ACPDeps(
        client_conn=client,
        session_id=f"test-{label}",
        tracker=tracker,
    )

    query = "Which classes in this codebase subclass from Protocol?"

    print(f"Query: {query}")
    print(f"Running inference...")

    start = time.perf_counter()
    result = await agent.run(query, deps=deps)
    elapsed = time.perf_counter() - start

    # Memory after
    mem_after = process.memory_info().rss / 1024 / 1024 / 1024  # GB
    mem_used = mem_after - mem_before

    # Count tool calls
    tool_calls = []
    if result.all_messages():
        for msg in result.all_messages():
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    if hasattr(part, "tool_name"):
                        tool_calls.append(part.tool_name)

    # Results
    print(f"\n{'=' * 80}")
    print(f"RESULTS: {label}")
    print(f"{'=' * 80}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Memory used: {mem_used:.2f} GB (baseline: {mem_before:.2f} GB)")
    print(f"Tool calls: {len(tool_calls)}")
    print(f"Tools used: {', '.join(tool_calls) if tool_calls else 'None'}")
    print(f"Autonomous: {'✅ Yes' if len(tool_calls) > 0 else '❌ No'}")
    print(f"\nResponse preview:")
    print(f"{result.output[:300]}...")
    print(f"{'=' * 80}\n")

    return {
        "label": label,
        "time": elapsed,
        "memory_baseline_gb": mem_before,
        "memory_used_gb": mem_used,
        "tool_calls": len(tool_calls),
        "autonomous": len(tool_calls) > 0,
        "response": result.output,
    }

async def main():
    """Run comparison."""
    print("=" * 80)
    print("DISTILLED MODEL COMPARISON")
    print("=" * 80)
    print("\nTesting 7B distilled model with LoRA adapter...")
    print("Query: 'Which classes in this codebase subclass from Protocol?'")

    # Test 7B distilled
    result_7b = await test_model(
        "local:http://127.0.0.1:8081/v1/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "7B Distilled"
    )

    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\n7B Distilled Model:")
    print(f"  Time: {result_7b['time']:.2f}s")
    print(f"  Memory: {result_7b['memory_used_gb']:.2f} GB")
    print(f"  Tool calls: {result_7b['tool_calls']}")
    print(f"  Autonomous: {result_7b['autonomous']}")

    print(f"\nPrevious 30B Baseline (from experiments):")
    print(f"  Time: ~25-30s")
    print(f"  Memory: ~16 GB")
    print(f"  Tool calls: 2+")
    print(f"  Autonomous: ✅ Yes")

    print(f"\n{'=' * 80}")
    print("METRICS")
    print(f"{'=' * 80}")
    speedup = 25 / result_7b['time']
    mem_reduction = 16 / result_7b['memory_used_gb']
    print(f"Speed improvement: {speedup:.1f}x faster")
    print(f"Memory reduction: {mem_reduction:.1f}x less memory")
    print(f"Autonomous capability: {'✅ Preserved' if result_7b['autonomous'] else '❌ Lost'}")

    return result_7b

if __name__ == "__main__":
    result = asyncio.run(main())
