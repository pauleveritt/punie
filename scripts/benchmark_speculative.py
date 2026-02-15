#!/usr/bin/env python3
"""Benchmark speculative decoding vs baseline for Phase 21.

Compares:
1. Baseline: 5-bit fused model (no draft)
2. Speculative: Same model + 1.5B draft model
3. Different num_draft_tokens values: 2, 3, 5

Measures:
- End-to-end latency (5-query discrimination test)
- Accuracy (must maintain 100%)
- Memory usage

Usage:
    uv run python scripts/benchmark_speculative.py
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import mlx.core as mx

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.agent.factory import create_pydantic_agent, create_server_model
from punie.local import LocalClient
from punie.training.server import ServerProcess
from punie.training.server_config import QWEN_STOP_SEQUENCES, ServerConfig
from punie.training.tool_call_parser import parse_tool_calls


# Standard 5-query discrimination test
TEST_QUERIES = [
    {
        "query": "Find all Django view functions",
        "expected": "tool",
        "description": "Search query - should use run_command",
    },
    {
        "query": "Show me the implementation of UserSerializer",
        "expected": "tool",
        "description": "Read query - should use read_file",
    },
    {
        "query": "What is dependency injection in Django?",
        "expected": "direct",
        "description": "Concept question - should answer directly",
    },
    {
        "query": "Find all uses of async/await in the codebase",
        "expected": "tool",
        "description": "Search query - should use run_command",
    },
    {
        "query": "What's the difference between Django ORM and raw SQL?",
        "expected": "direct",
        "description": "Comparison question - should answer directly",
    },
]


@dataclass(frozen=True)
class BenchmarkResult:
    """Results for a single benchmark configuration."""

    config_name: str
    draft_model: str | None
    num_draft_tokens: int | None
    total_time_ms: float
    avg_time_per_query_ms: float
    accuracy: float
    correct_count: int
    total_count: int
    memory_gb: float
    query_times: list[float]


async def benchmark_config(
    config_name: str,
    model_path: str,
    draft_model: str | None = None,
    num_draft_tokens: int | None = None,
) -> BenchmarkResult:
    """Benchmark a single configuration.

    Args:
        config_name: Human-readable config name
        model_path: Path to main model
        draft_model: Optional draft model path for speculative decoding
        num_draft_tokens: Optional number of draft tokens per step

    Returns:
        BenchmarkResult with timing and accuracy data
    """
    print(f"\n{'='*80}")
    print(f"Benchmarking: {config_name}")
    print('='*80)
    if draft_model:
        print(f"  Draft model: {draft_model}")
        print(f"  Draft tokens: {num_draft_tokens}")
    else:
        print("  Mode: Baseline (no speculative decoding)")
    print()

    # Create server config
    server_config = ServerConfig(
        model_path=model_path,
        port=8080,
        stop_sequences=QWEN_STOP_SEQUENCES,
        draft_model=draft_model,
        num_draft_tokens=num_draft_tokens,
    )

    # Start server
    print("Starting mlx_lm.server...")
    start_time = time.perf_counter()
    async with ServerProcess(config=server_config) as server:
        startup_time = time.perf_counter() - start_time
        print(f"✓ Server ready in {startup_time:.1f}s at {server.config.base_url}")

        # Get initial memory usage
        memory_gb = mx.metal.get_active_memory() / 1024**3
        print(f"  Memory: {memory_gb:.2f} GB")

        # Create agent
        model = create_server_model(server_config)
        agent_config = AgentConfig(
            temperature=0.0,  # Deterministic for benchmarking
            stop_sequences=QWEN_STOP_SEQUENCES,
        )
        agent = create_pydantic_agent(model=model, config=agent_config)

        # Create local client
        client = LocalClient(workspace=Path.cwd())

        # Run test queries
        print("\nRunning 5-query discrimination test...")
        query_times = []
        correct = 0

        total_start = time.perf_counter()

        for i, test in enumerate(TEST_QUERIES, 1):
            print(f"\n[{i}/5] {test['description']}")
            print(f"  Query: {test['query']}")

            # Create tracker and deps
            tracker = ToolCallTracker()
            deps = ACPDeps(
                client_conn=client,
                session_id=f"bench-{config_name}-{i}",
                tracker=tracker,
            )

            # Measure query time
            query_start = time.perf_counter()

            try:
                # Run agent
                result = await agent.run(test["query"], deps=deps)
                query_time_ms = (time.perf_counter() - query_start) * 1000
                query_times.append(query_time_ms)

                # Extract tool calls
                tool_calls_list = []
                if result.all_messages():
                    for msg in result.all_messages():
                        if hasattr(msg, "parts"):
                            for part in msg.parts:
                                if hasattr(part, "tool_name"):
                                    tool_calls_list.append(part.tool_name)
                if not tool_calls_list:
                    _, parsed_calls = parse_tool_calls(result.output)
                    tool_calls_list = [call["name"] for call in parsed_calls if "name" in call]

                # Check if correct
                used_tool = len(tool_calls_list) > 0
                expected_tool = test["expected"] == "tool"
                is_correct = used_tool == expected_tool

                if is_correct:
                    correct += 1

                status = "✓" if is_correct else "✗"
                print(f"  Expected: {test['expected']}, Got: {'tool' if used_tool else 'direct'} {status}")
                print(f"  Time: {query_time_ms:.1f}ms")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                query_time_ms = (time.perf_counter() - query_start) * 1000
                query_times.append(query_time_ms)

        total_time_ms = (time.perf_counter() - total_start) * 1000
        accuracy = (correct / len(TEST_QUERIES)) * 100
        avg_time_ms = total_time_ms / len(TEST_QUERIES)

        print(f"\n{'='*80}")
        print("RESULTS:")
        print(f"  Accuracy: {accuracy:.1f}% ({correct}/{len(TEST_QUERIES)})")
        print(f"  Total time: {total_time_ms:.1f}ms")
        print(f"  Avg per query: {avg_time_ms:.1f}ms")
        print(f"  Memory: {memory_gb:.2f} GB")
        print('='*80)

        return BenchmarkResult(
            config_name=config_name,
            draft_model=draft_model,
            num_draft_tokens=num_draft_tokens,
            total_time_ms=total_time_ms,
            avg_time_per_query_ms=avg_time_ms,
            accuracy=accuracy,
            correct_count=correct,
            total_count=len(TEST_QUERIES),
            memory_gb=memory_gb,
            query_times=query_times,
        )


async def run_all_benchmarks(model_path: str, draft_model: str) -> list[BenchmarkResult]:
    """Run all benchmark configurations.

    Args:
        model_path: Path to main 5-bit fused model
        draft_model: Path to draft model for speculative decoding

    Returns:
        List of BenchmarkResult for each configuration
    """
    results = []

    # Baseline (no speculative decoding)
    print("\n" + "="*80)
    print("CONFIGURATION 1/4: BASELINE")
    print("="*80)
    baseline = await benchmark_config("Baseline", model_path)
    results.append(baseline)

    # Speculative with num_draft_tokens=2
    print("\n" + "="*80)
    print("CONFIGURATION 2/4: SPECULATIVE (2 draft tokens)")
    print("="*80)
    spec_2 = await benchmark_config(
        "Speculative-2",
        model_path,
        draft_model=draft_model,
        num_draft_tokens=2,
    )
    results.append(spec_2)

    # Speculative with num_draft_tokens=3
    print("\n" + "="*80)
    print("CONFIGURATION 3/4: SPECULATIVE (3 draft tokens)")
    print("="*80)
    spec_3 = await benchmark_config(
        "Speculative-3",
        model_path,
        draft_model=draft_model,
        num_draft_tokens=3,
    )
    results.append(spec_3)

    # Speculative with num_draft_tokens=5
    print("\n" + "="*80)
    print("CONFIGURATION 4/4: SPECULATIVE (5 draft tokens)")
    print("="*80)
    spec_5 = await benchmark_config(
        "Speculative-5",
        model_path,
        draft_model=draft_model,
        num_draft_tokens=5,
    )
    results.append(spec_5)

    return results


def print_comparison(results: list[BenchmarkResult]) -> None:
    """Print comparison table of all benchmark results.

    Args:
        results: List of BenchmarkResult from all configurations
    """
    baseline = results[0]

    print("\n" + "="*80)
    print("COMPARISON TABLE")
    print("="*80)
    print()
    print(f"{'Configuration':<20} {'Avg Time':<12} {'Speedup':<10} {'Accuracy':<10} {'Memory':<10}")
    print("-" * 80)

    for result in results:
        speedup = baseline.avg_time_per_query_ms / result.avg_time_per_query_ms
        speedup_str = f"{speedup:.2f}x" if result != baseline else "1.00x"
        print(
            f"{result.config_name:<20} "
            f"{result.avg_time_per_query_ms:>8.1f}ms   "
            f"{speedup_str:<10} "
            f"{result.accuracy:>6.1f}%   "
            f"{result.memory_gb:>6.2f} GB"
        )

    print()
    print("="*80)
    print("FINDINGS")
    print("="*80)

    # Find best speculative config
    spec_results = results[1:]
    if spec_results:
        best_spec = min(spec_results, key=lambda r: r.avg_time_per_query_ms)
        speedup = baseline.avg_time_per_query_ms / best_spec.avg_time_per_query_ms
        improvement_pct = ((baseline.avg_time_per_query_ms - best_spec.avg_time_per_query_ms) / baseline.avg_time_per_query_ms) * 100

        print(f"\n✅ Best configuration: {best_spec.config_name}")
        print(f"   - Speedup: {speedup:.2f}x ({improvement_pct:.1f}% faster)")
        print(f"   - Accuracy: {best_spec.accuracy:.1f}% (target: 100%)")
        print(f"   - Memory: {best_spec.memory_gb:.2f} GB (vs {baseline.memory_gb:.2f} GB baseline)")

        if best_spec.accuracy < 100:
            print(f"\n⚠️  WARNING: Accuracy dropped to {best_spec.accuracy:.1f}%")
            print("   Speculative decoding may be affecting quality")
        else:
            print("\n✓  Quality maintained (100% accuracy)")

        if speedup < 1.2:
            print(f"\n⚠️  WARNING: Speedup is only {speedup:.2f}x")
            print("   Speculative decoding may not be worth the complexity")
        elif speedup >= 1.5:
            print(f"\n✅ EXCELLENT: {speedup:.2f}x speedup is significant!")
            print("   Recommend deploying speculative decoding")
        else:
            print(f"\n✓  Moderate speedup: {speedup:.2f}x")
            print("   Consider deployment based on latency requirements")

    print("="*80)


def save_results(results: list[BenchmarkResult]) -> Path:
    """Save benchmark results to JSON file.

    Args:
        results: List of BenchmarkResult from all configurations

    Returns:
        Path to saved JSON file
    """
    output_file = Path("logs/phase21_speculative_benchmark.json")
    output_file.parent.mkdir(exist_ok=True)

    data = {
        "timestamp": datetime.now().isoformat(),
        "model_path": "fused_model_qwen3_phase21_xml_5bit",
        "draft_model": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
        "results": [
            {
                "config_name": r.config_name,
                "draft_model": r.draft_model,
                "num_draft_tokens": r.num_draft_tokens,
                "total_time_ms": r.total_time_ms,
                "avg_time_per_query_ms": r.avg_time_per_query_ms,
                "accuracy": r.accuracy,
                "correct_count": r.correct_count,
                "total_count": r.total_count,
                "memory_gb": r.memory_gb,
                "query_times": r.query_times,
            }
            for r in results
        ],
        "comparison": {
            "baseline_avg_ms": results[0].avg_time_per_query_ms,
            "best_spec_avg_ms": min(r.avg_time_per_query_ms for r in results[1:]),
            "best_speedup": results[0].avg_time_per_query_ms / min(r.avg_time_per_query_ms for r in results[1:]),
            "all_100_accuracy": all(r.accuracy == 100.0 for r in results),
        },
    }

    with output_file.open("w") as f:
        json.dump(data, f, indent=2)

    return output_file


def main():
    """Run speculative decoding benchmarks and save results."""
    print("="*80)
    print("PHASE 21: SPECULATIVE DECODING BENCHMARK")
    print("="*80)
    print()
    print("Configurations to test:")
    print("  1. Baseline (no speculative decoding)")
    print("  2. Speculative with 2 draft tokens")
    print("  3. Speculative with 3 draft tokens")
    print("  4. Speculative with 5 draft tokens")
    print()
    print("Model: fused_model_qwen3_phase21_xml_5bit (Qwen3-30B-A3B)")
    print("Draft: mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit")
    print()

    # Check if main model exists
    model_path = "fused_model_qwen3_phase21_xml_5bit"
    if not Path(model_path).exists():
        print(f"Error: Model not found at {model_path}")
        print("Please ensure the 5-bit fused model is available.")
        return 1

    draft_model = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"

    # Run all benchmarks
    results = asyncio.run(run_all_benchmarks(model_path, draft_model))

    # Print comparison
    print_comparison(results)

    # Save results
    output_file = save_results(results)
    print(f"\n✅ Results saved to {output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
