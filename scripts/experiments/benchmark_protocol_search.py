"""Benchmark: Protocol Search - 30B vs Claude Code

Compares warm performance and quality for:
"What classes in this codebase implement a protocol?"

Metrics:
- Execution time (seconds)
- Tool calls count
- Accuracy (% of 6 Protocol classes found)
- Answer quality (subjective assessment)

Context: 30B crashed system with 16GB RAM usage.
Goal: Quantify performance to inform smaller model requirements.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from punie.agent.config import AgentConfig, ServerConfig
from punie.agent.pydantic_agent import create_pydantic_agent


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    model_name: str
    execution_time: float  # seconds
    tool_calls: int
    response: str
    classes_found: list[str]  # Protocol class names found
    accuracy: float  # % of expected classes found


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
    """Calculate accuracy by checking which expected classes are mentioned.

    Args:
        response: Model's response text
        expected: List of expected class names

    Returns:
        Tuple of (classes_found, accuracy_percentage)
    """
    found = [cls for cls in expected if cls in response]
    accuracy = len(found) / len(expected) if expected else 0.0
    return found, accuracy


async def benchmark_30b_warm(workspace: Path) -> BenchmarkResult:
    """Benchmark 30B model with warm start (model already loaded).

    Args:
        workspace: Project root directory

    Returns:
        Benchmark results
    """
    print("🔥 Warming up 30B model (loading if needed)...")

    config = AgentConfig(
        server=ServerConfig(
            model_path="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
            port=8080,
        ),
        workspace=workspace,
    )

    agent = create_pydantic_agent(config)

    # Warm-up call (not measured)
    await agent.run(
        "What is 2+2?",
        message_history=[],
    )

    print("✅ Model warmed up. Starting timed run...\n")

    # Actual timed run
    start_time = time.time()
    result = await agent.run(
        PROTOCOL_SEARCH_QUERY,
        message_history=[],
    )
    execution_time = time.time() - start_time

    # Count tool calls
    tool_calls = len([msg for msg in result.all_messages() if msg.role == "tool"])

    # Calculate accuracy
    classes_found, accuracy = calculate_accuracy(result.data, EXPECTED_CLASSES)

    return BenchmarkResult(
        model_name="Qwen3-Coder-30B-4bit (warm)",
        execution_time=execution_time,
        tool_calls=tool_calls,
        response=result.data,
        classes_found=classes_found,
        accuracy=accuracy,
    )


def benchmark_claude_code_manual() -> BenchmarkResult:
    """Placeholder for manual Claude Code benchmark.

    User should run this query in Claude Code and manually enter results.
    """
    print("\n" + "=" * 80)
    print("MANUAL BENCHMARK: Claude Code")
    print("=" * 80)
    print(f"\nQuery: {PROTOCOL_SEARCH_QUERY}")
    print("\nPlease run this query in Claude Code and record:")
    print("1. Execution time (seconds)")
    print("2. Number of tool calls")
    print("3. Response text")
    print("\nPress Enter when ready to input results...")
    input()

    exec_time = float(input("Execution time (seconds): "))
    tool_calls = int(input("Number of tool calls: "))
    print("\nPaste response (end with Ctrl+D on empty line):")

    response_lines = []
    try:
        while True:
            line = input()
            response_lines.append(line)
    except EOFError:
        pass

    response = "\n".join(response_lines)

    classes_found, accuracy = calculate_accuracy(response, EXPECTED_CLASSES)

    return BenchmarkResult(
        model_name="Claude Code (Sonnet 4.5)",
        execution_time=exec_time,
        tool_calls=tool_calls,
        response=response,
        classes_found=classes_found,
        accuracy=accuracy,
    )


def print_comparison(results: list[BenchmarkResult]) -> None:
    """Print side-by-side comparison of benchmark results.

    Args:
        results: List of benchmark results to compare
    """
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS: Protocol Search Comparison")
    print("=" * 80)

    # Performance metrics
    print("\n## Performance Metrics\n")
    print(f"{'Model':<35} {'Time (s)':<12} {'Tool Calls':<12} {'Accuracy':<12}")
    print("-" * 71)

    for result in results:
        print(
            f"{result.model_name:<35} "
            f"{result.execution_time:<12.2f} "
            f"{result.tool_calls:<12} "
            f"{result.accuracy:<12.1%}"
        )

    # Accuracy details
    print("\n## Classes Found\n")
    for result in results:
        print(f"{result.model_name}:")
        for cls in EXPECTED_CLASSES:
            found = "✅" if cls in result.classes_found else "❌"
            print(f"  {found} {cls}")
        print()

    # Speed comparison
    if len(results) == 2:
        speedup = results[1].execution_time / results[0].execution_time
        faster = results[0].model_name if speedup > 1 else results[1].model_name
        print(f"\n## Speed: {faster} is {abs(speedup):.2f}x faster")

    # Memory note
    print("\n## Resource Usage\n")
    for result in results:
        if "30B" in result.model_name:
            print(f"{result.model_name}: ~16GB RAM (crashed user's Mac)")
        else:
            print(f"{result.model_name}: Cloud-based (no local RAM)")

    print("\n" + "=" * 80)


async def main() -> None:
    """Run benchmark comparing 30B warm vs Claude Code."""
    workspace = Path.cwd()

    print("🏁 Starting Protocol Search Benchmark")
    print(f"📁 Workspace: {workspace}\n")

    # Run 30B warm benchmark
    result_30b = await benchmark_30b_warm(workspace)

    print(f"\n✅ 30B completed in {result_30b.execution_time:.2f}s")
    print(f"   Tool calls: {result_30b.tool_calls}")
    print(f"   Accuracy: {result_30b.accuracy:.1%}")

    # Get Claude Code results manually
    result_claude = benchmark_claude_code_manual()

    # Print comparison
    print_comparison([result_30b, result_claude])

    # Save results
    output_file = workspace / "benchmark_protocol_results.txt"
    with output_file.open("w") as f:
        f.write("=" * 80 + "\n")
        f.write("PROTOCOL SEARCH BENCHMARK RESULTS\n")
        f.write("=" * 80 + "\n\n")

        for result in [result_30b, result_claude]:
            f.write(f"\n## {result.model_name}\n\n")
            f.write(f"Execution time: {result.execution_time:.2f}s\n")
            f.write(f"Tool calls: {result.tool_calls}\n")
            f.write(f"Accuracy: {result.accuracy:.1%}\n")
            f.write(f"Classes found: {', '.join(result.classes_found)}\n\n")
            f.write("Response:\n")
            f.write("-" * 80 + "\n")
            f.write(result.response)
            f.write("\n" + "-" * 80 + "\n")

    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
