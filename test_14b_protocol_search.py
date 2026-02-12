#!/usr/bin/env python3
"""Test 14B model - potential sweet spot between 7B and 30B."""

import asyncio
import time
from pathlib import Path

from punie.agent.factory import create_pydantic_agent
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.local import LocalClient


EXPECTED_CLASSES = [
    "HttpAppFactory",
    "Client",
    "Agent",
    "MessageDispatcher",
    "MessageQueue",
    "MessageStateStore",
]

PROTOCOL_SEARCH_QUERY = "What classes in this codebase implement a protocol?"


async def main():
    """Test 14B model on Protocol search."""
    print("=" * 80)
    print("14B MODEL: Protocol Search Test (Potential Sweet Spot!)")
    print("=" * 80)

    workspace = Path.cwd()
    model_name = "local:http://127.0.0.1:8080/v1/qwen/qwen3-14b"

    print(f"\nModel: qwen/qwen3-14b")
    print(f"Query: {PROTOCOL_SEARCH_QUERY}\n")

    agent_config = AgentConfig(temperature=0.0)
    agent = create_pydantic_agent(model=model_name, config=agent_config)
    client = LocalClient(workspace=workspace)

    # Warmup
    print("Warming up...")
    warmup_tracker = ToolCallTracker()
    warmup_deps = ACPDeps(client_conn=client, session_id="warmup", tracker=warmup_tracker)
    await agent.run("What is 2+2?", deps=warmup_deps)
    print("✅ Ready!\n")

    # Protocol search
    print("=" * 80)
    print("Running Protocol Search (TIMED)")
    print("=" * 80)

    tracker = ToolCallTracker()
    deps = ACPDeps(client_conn=client, session_id="protocol-search", tracker=tracker)

    start_time = time.perf_counter()
    result = await agent.run(PROTOCOL_SEARCH_QUERY, deps=deps)
    execution_time = time.perf_counter() - start_time

    # Count tool calls
    tool_calls = []
    if result.all_messages():
        for msg in result.all_messages():
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    if hasattr(part, "tool_name"):
                        tool_calls.append(part.tool_name)

    # Calculate accuracy
    found = [cls for cls in EXPECTED_CLASSES if cls in result.output]
    accuracy = len(found) / len(EXPECTED_CLASSES)

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\n⏱️  Execution time: {execution_time:.2f}s")
    print(f"🔧 Tool calls: {len(tool_calls)}")
    if tool_calls:
        print(f"   Tools used: {', '.join(tool_calls)}")
    print(f"🎯 Accuracy: {accuracy:.1%} ({len(found)}/{len(EXPECTED_CLASSES)})")

    print(f"\n📋 Classes found:")
    for cls in EXPECTED_CLASSES:
        status = "✅" if cls in found else "❌"
        print(f"   {status} {cls}")

    print(f"\n📝 Response:")
    print("-" * 80)
    print(result.output)
    print("-" * 80)

    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    print(f"\n{'Model':<20} {'Time':<12} {'Tools':<8} {'Accuracy':<12} {'RAM':<12}")
    print("-" * 64)
    print(f"{'Claude Code':<20} {'10.76s':<12} {'2':<8} {'100%':<12} {'0 GB':<12}")
    print(f"{'7B':<20} {'8.07s':<12} {'0':<8} {'0%':<12} {'4-6 GB':<12}")
    time_str = f"{execution_time:.2f}s"
    print(f"{'14B (THIS RUN)':<20} {time_str:<12} {f'{len(tool_calls)}':<8} {f'{accuracy:.1%}':<12} {'~8-10 GB':<12}")
    print(f"{'30B':<20} {'30.83s':<12} {'2':<8} {'100%':<12} {'16 GB':<12}")

    # Analysis
    autonomous = len(tool_calls) > 0 and accuracy >= 0.5
    print(f"\n🤖 Autonomous Reasoning: {'✅ YES' if autonomous else '❌ NO'}")

    if autonomous and accuracy == 1.0:
        print("\n🎉 SWEET SPOT FOUND!")
        print("   ✅ Autonomous tool usage")
        print("   ✅ 100% accuracy")
        print(f"   ✅ {execution_time:.1f}s latency (acceptable)")
        print("   ✅ ~8-10GB RAM (half of 30B)")
        print("\n   Recommendation: Use 14B as baseline, skip 30B distillation!")
    elif autonomous:
        print(f"\n⚠️  Partial success - {accuracy:.1%} accuracy")
        print("   May need fine-tuning or more examples")
    else:
        print("\n❌ No autonomous reasoning - stick with 30B for distillation")

    # Save results
    with open("test_14b_protocol_results.txt", "w") as f:
        f.write("14B Model: Protocol Search Results\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Model: qwen/qwen3-14b\n")
        f.write(f"Execution time: {execution_time:.2f}s\n")
        f.write(f"Tool calls: {len(tool_calls)}\n")
        f.write(f"Accuracy: {accuracy:.1%}\n")
        f.write(f"Autonomous: {autonomous}\n\n")
        f.write("Response:\n")
        f.write(result.output)

    print(f"\n💾 Results saved to: test_14b_protocol_results.txt")


if __name__ == "__main__":
    asyncio.run(main())
