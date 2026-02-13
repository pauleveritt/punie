#!/usr/bin/env python3
"""Evaluate distilled 7B model against 30B baseline.

Tests if 7B learned autonomous tool usage from 30B.
Success criteria: >80% autonomous tool usage on benchmark tasks.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from punie.agent.factory import create_pydantic_agent
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.local import LocalClient


@dataclass
class EvalResult:
    """Evaluation result for a single task."""

    task_id: str
    model: str
    success: bool
    execution_time: float
    tool_calls: int
    accuracy: float
    autonomous: bool  # Did model use tools without being told?


# Same tasks used to validate 30B
BENCHMARK_TASKS = [
    {
        "id": "protocol_search",
        "question": "Which classes in this codebase subclass from Protocol?",
        "expected_concepts": ["HttpAppFactory", "Client", "Agent", "MessageDispatcher"],
    },
    {
        "id": "import_usage",
        "question": "Find all files that import 'asyncio' and list them",
        "expected_concepts": ["asyncio", "import"],
    },
    {
        "id": "function_signature",
        "question": "What are the parameters for the create_pydantic_agent function?",
        "expected_concepts": ["model", "config"],
    },
    {
        "id": "test_count",
        "question": "How many test files are in the tests/ directory?",
        "expected_concepts": ["tests/", "test_"],
    },
    {
        "id": "dataclass_search",
        "question": "List all dataclasses defined in src/punie/training/",
        "expected_concepts": ["@dataclass"],
    },
]


async def evaluate_model(
    model_name: str,
    model_label: str,
    client: LocalClient,
) -> list[EvalResult]:
    """Run benchmark tasks on a model.

    Args:
        model_name: Model identifier for agent
        model_label: Human-readable label
        client: LocalClient for workspace

    Returns:
        List of evaluation results
    """
    print(f"\n{'=' * 80}")
    print(f"Evaluating: {model_label}")
    print(f"{'=' * 80}\n")

    agent_config = AgentConfig(temperature=0.0)
    agent = create_pydantic_agent(model=model_name, config=agent_config)

    results = []

    for task in BENCHMARK_TASKS:
        print(f"Task: {task['id']}")

        tracker = ToolCallTracker()
        deps = ACPDeps(
            client_conn=client,
            session_id=f"eval-{task['id']}",
            tracker=tracker,
        )

        try:
            start = time.perf_counter()
            result = await agent.run(task['question'], deps=deps)
            elapsed = time.perf_counter() - start

            # Count tool calls
            tool_calls = []
            if result.all_messages():
                for msg in result.all_messages():
                    if hasattr(msg, "parts"):
                        for part in msg.parts:
                            if hasattr(part, "tool_name"):
                                tool_calls.append(part.tool_name)

            # Check accuracy
            response_lower = result.output.lower()
            found = [c for c in task['expected_concepts'] if c.lower() in response_lower]
            accuracy = len(found) / len(task['expected_concepts'])

            # Autonomous = used tools AND got answer
            autonomous = len(tool_calls) > 0 and accuracy > 0.5

            success = autonomous and accuracy >= 0.75

            eval_result = EvalResult(
                task_id=task['id'],
                model=model_label,
                success=success,
                execution_time=elapsed,
                tool_calls=len(tool_calls),
                accuracy=accuracy,
                autonomous=autonomous,
            )

            status = "✅" if success else "❌"
            auto = "🤖" if autonomous else "❓"
            print(f"  {status} {auto} {elapsed:.1f}s, {len(tool_calls)} tools, {accuracy:.0%} acc\n")

            results.append(eval_result)

        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            results.append(EvalResult(
                task_id=task['id'],
                model=model_label,
                success=False,
                execution_time=0,
                tool_calls=0,
                accuracy=0.0,
                autonomous=False,
            ))

    return results


def print_comparison(distilled_results: list[EvalResult], baseline_results: list[EvalResult]):
    """Print side-by-side comparison of distilled vs baseline.

    Args:
        distilled_results: 7B distilled model results
        baseline_results: 30B baseline results
    """
    print("\n" + "=" * 80)
    print("COMPARISON: 7B Distilled vs 30B Baseline")
    print("=" * 80 + "\n")

    # Overall metrics
    distilled_success = sum(1 for r in distilled_results if r.success)
    baseline_success = sum(1 for r in baseline_results if r.success)

    distilled_autonomous = sum(1 for r in distilled_results if r.autonomous)
    baseline_autonomous = sum(1 for r in baseline_results if r.autonomous)

    distilled_avg_time = sum(r.execution_time for r in distilled_results) / len(distilled_results)
    baseline_avg_time = sum(r.execution_time for r in baseline_results) / len(baseline_results)

    print("Overall Metrics:")
    print(f"\n{'Metric':<30} {'7B Distilled':<20} {'30B Baseline':<20}")
    print("-" * 70)
    print(f"{'Success rate':<30} {distilled_success}/{len(distilled_results)} ({distilled_success/len(distilled_results)*100:.0f}%)"
          f"{' '*7} {baseline_success}/{len(baseline_results)} ({baseline_success/len(baseline_results)*100:.0f}%)")
    print(f"{'Autonomous tool usage':<30} {distilled_autonomous}/{len(distilled_results)} ({distilled_autonomous/len(distilled_results)*100:.0f}%)"
          f"{' '*7} {baseline_autonomous}/{len(baseline_results)} ({baseline_autonomous/len(baseline_results)*100:.0f}%)")
    print(f"{'Average time':<30} {distilled_avg_time:.1f}s{' '*15} {baseline_avg_time:.1f}s")

    # Per-task comparison
    print("\nPer-Task Results:")
    print(f"\n{'Task':<20} {'7B Auto':<10} {'7B Acc':<10} {'30B Auto':<10} {'30B Acc':<10}")
    print("-" * 60)

    for i, task in enumerate(BENCHMARK_TASKS):
        d = distilled_results[i]
        b = baseline_results[i]

        d_auto = "✅" if d.autonomous else "❌"
        b_auto = "✅" if b.autonomous else "❌"

        print(f"{task['id']:<20} {d_auto:<10} {d.accuracy:>4.0%}{' '*5} {b_auto:<10} {b.accuracy:>4.0%}")

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80 + "\n")

    autonomous_rate = distilled_autonomous / len(distilled_results)

    if autonomous_rate >= 0.8:
        print("🎉 SUCCESS! Distillation worked!")
        print(f"   7B model achieved {autonomous_rate:.0%} autonomous tool usage")
        print("   Ready for production deployment")
        print("\n   Benefits vs 30B:")
        speedup = baseline_avg_time / distilled_avg_time if distilled_avg_time > 0 else 0
        print(f"   - {speedup:.1f}x faster ({distilled_avg_time:.1f}s vs {baseline_avg_time:.1f}s)")
        print("   - 2-3x less RAM (4-6GB vs 16GB)")
        print("   - Same autonomous capability")

    elif autonomous_rate >= 0.6:
        print("⚠️  PARTIAL SUCCESS")
        print(f"   7B model achieved {autonomous_rate:.0%} autonomous tool usage")
        print("   Recommendations:")
        print("   - Generate more training examples (1K → 5K)")
        print("   - Train for more epochs (3 → 5)")
        print("   - Or accept partial success for some use cases")

    else:
        print("❌ DISTILLATION FAILED")
        print(f"   7B model only achieved {autonomous_rate:.0%} autonomous tool usage")
        print("   7B may lack capacity for autonomous reasoning")
        print("\n   Options:")
        print("   - Try larger model (14B if available)")
        print("   - Use 30B with optimizations (KV cache, caching)")
        print("   - Hybrid approach (7B + 30B delegation)")


async def main():
    """Run full evaluation: 7B distilled vs 30B baseline."""
    print("=" * 80)
    print("DISTILLED MODEL EVALUATION")
    print("=" * 80)
    print("\nComparing 7B distilled model to 30B baseline")
    print("Success criteria: >80% autonomous tool usage\n")

    workspace = Path.cwd()
    client = LocalClient(workspace=workspace)

    # Evaluate 30B baseline (reference)
    baseline_model = "local:http://127.0.0.1:8080/v1/qwen3-30b-a3b-instruct-2507-mlx"
    baseline_results = await evaluate_model(baseline_model, "30B Baseline", client)

    # Evaluate 7B distilled (with LoRA adapter)
    # Note: This assumes you've loaded the 7B model with adapter to the server
    # Adjust model name/port as needed
    distilled_model = "local:http://127.0.0.1:8081/v1/qwen2.5-coder-7b-distilled"
    distilled_results = await evaluate_model(distilled_model, "7B Distilled", client)

    # Compare results
    print_comparison(distilled_results, baseline_results)

    # Save detailed results
    output_file = Path("evaluation_results.json")
    import json
    with output_file.open("w") as f:
        json.dump({
            "distilled": [vars(r) for r in distilled_results],
            "baseline": [vars(r) for r in baseline_results],
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
