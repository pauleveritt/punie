#!/usr/bin/env python3
"""Test 7B model on Protocol search - finding the sweet spot.

Hypothesis: 7B might provide autonomous reasoning (like 30B) with lower resource cost.

Comparison targets:
- 1.5B: Fast but no autonomous reasoning (hallucinates)
- 7B: ??? (this test)
- 30B: Autonomous but too slow/heavy (16GB RAM, 93s, crashed system)
- Claude Code: Fast and accurate but cloud-based (10.76s, 2 tools)

Goal: 7B should be:
- <30s execution time (vs 93s for 30B)
- <8GB RAM (vs 16GB for 30B)
- Autonomous tool usage (unlike 1.5B)
- 100% accuracy on Protocol search
"""

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


# Expected Protocol classes in codebase
EXPECTED_CLASSES = [
    "HttpAppFactory",  # src/punie/http/types.py
    "Client",  # src/punie/acp/interfaces.py
    "Agent",  # src/punie/acp/interfaces.py
    "MessageDispatcher",  # src/punie/acp/task/dispatcher.py
    "MessageQueue",  # src/punie/acp/task/queue.py
    "MessageStateStore",  # src/punie/acp/task/state.py
]

PROTOCOL_SEARCH_QUERY = "What classes in this codebase implement a protocol?"


def calculate_accuracy(response: str, expected: list[str]) -> tuple[list[str], float]:
    """Calculate accuracy by checking which expected classes are mentioned."""
    found = [cls for cls in expected if cls in response]
    accuracy = len(found) / len(expected) if expected else 0.0
    return found, accuracy


async def test_7b_protocol_search():
    """Test 7B model on Protocol search query."""
    print("=" * 80)
    print("7B MODEL: Protocol Search Test")
    print("=" * 80)
    print(f"\nQuery: {PROTOCOL_SEARCH_QUERY}")
    print("\nExpected classes:")
    for cls in EXPECTED_CLASSES:
        print(f"  - {cls}")
    print()

    # Try Qwen2.5-Coder-7B first (more common), fallback to Qwen3 if needed
    model_path = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8081,  # Different port from 30B (8080)
    )

    print(f"Model: {model_path}")
    print(f"Port: {server_config.port}")
    print(f"Workspace: {workspace}")

    print("\n" + "=" * 80)
    print("Starting server (this may take 20-30s to load model)...")
    print("=" * 80)

    server = ServerProcess(config=server_config)

    try:
        await server.start(timeout=180.0)  # 3 minutes for model loading
        print("✅ Server started successfully")

        # Create agent
        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)
        client = LocalClient(workspace=workspace)

        # Warmup
        print("\n" + "=" * 80)
        print("Warming up model (test query: 'What is 2+2?')...")
        print("=" * 80)

        warmup_tracker = ToolCallTracker()
        warmup_deps = ACPDeps(
            client_conn=client,
            session_id="warmup",
            tracker=warmup_tracker,
        )

        warmup_start = time.perf_counter()
        await agent.run("What is 2+2?", deps=warmup_deps)
        warmup_time = time.perf_counter() - warmup_start

        print(f"✅ Warmup complete ({warmup_time:.2f}s)")

        # Actual test
        print("\n" + "=" * 80)
        print("Running Protocol Search (TIMED)")
        print("=" * 80)

        tracker = ToolCallTracker()
        deps = ACPDeps(
            client_conn=client,
            session_id="protocol-search",
            tracker=tracker,
        )

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
        classes_found, accuracy = calculate_accuracy(result.output, EXPECTED_CLASSES)

        # Print results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        print(f"\n⏱️  Execution time: {execution_time:.2f}s")
        print(f"🔧 Tool calls: {len(tool_calls)}")
        if tool_calls:
            print(f"   Tools used: {', '.join(tool_calls)}")
        print(f"🎯 Accuracy: {accuracy:.1%} ({len(classes_found)}/{len(EXPECTED_CLASSES)} classes found)")

        print("\n📋 Classes found:")
        for cls in EXPECTED_CLASSES:
            found = "✅" if cls in classes_found else "❌"
            print(f"   {found} {cls}")

        print("\n📝 Response:")
        print("-" * 80)
        print(result.output)
        print("-" * 80)

        # Comparison to benchmarks
        print("\n" + "=" * 80)
        print("COMPARISON TO BENCHMARKS")
        print("=" * 80)

        print(f"\n{'Model':<20} {'Time':<12} {'Tools':<8} {'Accuracy':<12} {'RAM':<12}")
        print("-" * 64)
        print(f"{'Claude Code':<20} {'10.76s':<12} {'2':<8} {'100%':<12} {'0 GB':<12}")
        print(f"{'7B (THIS RUN)':<20} {f'{execution_time:.2f}s':<12} {f'{len(tool_calls)}':<8} {f'{accuracy:.1%}':<12} {'~4-6 GB':<12}")
        print(f"{'30B (previous)':<20} {'93.49s':<12} {'6':<8} {'100%':<12} {'16 GB ❌':<12}")

        # Speed comparison
        speedup_vs_30b = 93.49 / execution_time
        slowdown_vs_claude = execution_time / 10.76

        print("\n📊 Speed Analysis:")
        print(f"   vs 30B: {speedup_vs_30b:.2f}x FASTER ✅")
        print(f"   vs Claude Code: {slowdown_vs_claude:.2f}x SLOWER")

        # Autonomous reasoning check
        autonomous = len(tool_calls) > 0 and accuracy >= 0.5
        print(f"\n🤖 Autonomous Reasoning: {'✅ YES' if autonomous else '❌ NO'}")
        if autonomous:
            print("   Model decided to use tools without being told!")
        else:
            print("   Model didn't use tools or hallucinated answer")

        # Viability assessment
        print("\n🎯 Production Viability:")
        viable = (
            execution_time < 30  # Under 30s
            and accuracy == 1.0  # 100% accurate
            and autonomous  # Uses tools autonomously
        )

        if viable:
            print("   ✅ VIABLE - Fast enough, accurate, and autonomous!")
            print(f"      → {execution_time:.1f}s latency is acceptable for codebase exploration")
            print("      → 4-6GB RAM is sustainable on most dev machines")
            print("      → Can proceed with fine-tuning for optimization")
        elif autonomous and accuracy == 1.0:
            print(f"   ⚠️  MARGINAL - Accurate and autonomous but slow ({execution_time:.1f}s)")
            print("      → May still be viable if fine-tuning improves speed")
            print("      → Consider caching common queries")
        else:
            print("   ❌ NOT VIABLE - Missing autonomous reasoning or accuracy")
            print("      → Need to try different approach (distillation, larger model, etc.)")

        # Save results
        output_file = workspace / "test_7b_protocol_results.txt"
        with output_file.open("w") as f:
            f.write("7B Model: Protocol Search Results\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Model: {model_path}\n")
            f.write(f"Query: {PROTOCOL_SEARCH_QUERY}\n\n")
            f.write(f"Execution time: {execution_time:.2f}s\n")
            f.write(f"Tool calls: {len(tool_calls)}\n")
            f.write(f"Tools used: {', '.join(tool_calls)}\n")
            f.write(f"Accuracy: {accuracy:.1%} ({len(classes_found)}/{len(EXPECTED_CLASSES)})\n")
            f.write(f"Classes found: {', '.join(classes_found)}\n\n")
            f.write(f"Autonomous: {autonomous}\n")
            f.write(f"Viable: {viable}\n\n")
            f.write("Response:\n")
            f.write("-" * 80 + "\n")
            f.write(result.output)
            f.write("\n" + "-" * 80 + "\n")

        print(f"\n💾 Results saved to: {output_file}")

    finally:
        print("\n" + "=" * 80)
        print("Shutting down server...")
        print("=" * 80)
        await server.stop()
        print("✅ Server stopped")


if __name__ == "__main__":
    asyncio.run(test_7b_protocol_search())
