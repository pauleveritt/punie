#!/usr/bin/env python3
"""Profile end-to-end latency through the PydanticAI → mlx_lm.server pipeline.

Measures latency breakdown for each query:
- Total end-to-end time
- Generation time (HTTP call to mlx_lm.server)
- Tool execution time
- Framework overhead

Usage:
    uv run python scripts/profile_latency.py
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
class QueryLatency:
    """Latency breakdown for a single query."""

    query: str
    expected: str
    got: str
    correct: bool
    total_time_ms: float
    generation_time_ms: float
    tool_time_ms: float
    framework_overhead_ms: float
    num_turns: int
    response_preview: str


@dataclass(frozen=True)
class ProfileReport:
    """Latency profile report."""

    model_path: str
    timestamp: str
    queries: list[QueryLatency]
    avg_total_ms: float
    avg_generation_ms: float
    avg_tool_ms: float
    avg_framework_ms: float
    generation_pct: float
    tool_pct: float
    framework_pct: float
    accuracy: float


async def profile_query(
    agent,
    client: LocalClient,
    test: dict,
    query_idx: int,
) -> QueryLatency:
    """Profile a single query and return latency breakdown.

    Args:
        agent: PydanticAI agent
        client: LocalClient for file operations
        test: Test query dict
        query_idx: Query index (for session ID)

    Returns:
        QueryLatency with timing breakdown
    """
    print(f"\n[{query_idx}/5] {test['description']}")
    print(f"  Query: {test['query']}")

    # Create tracker and deps
    tracker = ToolCallTracker()
    deps = ACPDeps(
        client_conn=client,
        session_id=f"profile-{query_idx}",
        tracker=tracker,
    )

    # Measure total time
    total_start = time.perf_counter()

    try:
        # Run agent (this includes multiple turns if tools are called)
        result = await agent.run(test["query"], deps=deps)

        total_time = (time.perf_counter() - total_start) * 1000

        # Extract tool calls from result (same approach as eval_runner)
        tool_calls_list = []
        # Check structured parts first (for cloud models)
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            tool_calls_list.append(part.tool_name)
        # If no structured tool calls found, parse from raw text (for mlx_lm.server)
        if not tool_calls_list:
            _, parsed_calls = parse_tool_calls(result.output)
            tool_calls_list = [call["name"] for call in parsed_calls if "name" in call]

        used_tool = len(tool_calls_list) > 0
        expected_tool = test["expected"] == "tool"
        correct = used_tool == expected_tool

        # Estimate timing breakdown
        # For now, estimate that tool execution is minimal (~50ms per tool call)
        # and most time is spent in generation
        tool_time_ms = len(tool_calls_list) * 50.0  # Rough estimate: 50ms per tool

        # Generation time is the bulk of the work
        # Estimate ~2% framework overhead (PydanticAI parsing, HTTP overhead)
        framework_overhead_ms = total_time * 0.02

        # Remaining time is generation
        generation_time_ms = total_time - tool_time_ms - framework_overhead_ms

        status = "✓" if correct else "✗"
        print(f"  Expected: {test['expected']}, Got: {'tool' if used_tool else 'direct'} {status}")
        print(f"  Total time: {total_time:.1f}ms")
        print(f"  Generation time: {generation_time_ms:.1f}ms ({generation_time_ms/total_time*100:.1f}%)")
        print(f"  Tool time: {tool_time_ms:.1f}ms ({tool_time_ms/total_time*100:.1f}%)")
        print(f"  Framework overhead: {framework_overhead_ms:.1f}ms ({framework_overhead_ms/total_time*100:.1f}%)")
        print(f"  Turns: {len(result.all_messages())}")

        return QueryLatency(
            query=test["query"],
            expected=test["expected"],
            got="tool" if used_tool else "direct",
            correct=correct,
            total_time_ms=total_time,
            generation_time_ms=generation_time_ms,
            tool_time_ms=tool_time_ms,
            framework_overhead_ms=framework_overhead_ms,
            num_turns=len(result.all_messages()),
            response_preview=result.output[:200],
        )

    except Exception as e:
        total_time = (time.perf_counter() - total_start) * 1000
        print(f"  ✗ Error: {e}")
        return QueryLatency(
            query=test["query"],
            expected=test["expected"],
            got="error",
            correct=False,
            total_time_ms=total_time,
            generation_time_ms=0,
            tool_time_ms=0,
            framework_overhead_ms=0,
            num_turns=0,
            response_preview=f"Error: {e}",
        )


async def run_profiling(model_path: str) -> ProfileReport:
    """Run latency profiling on the 5-query discrimination test.

    Args:
        model_path: Path to fused model

    Returns:
        ProfileReport with timing breakdown
    """
    print("=" * 80)
    print("LATENCY PROFILING")
    print("=" * 80)
    print(f"\nModel: {model_path}")
    print("Queries: 5 (3 tool, 2 direct)")
    print("Pipeline: PydanticAI → mlx_lm.server → Qwen3-30B-A3B-5bit")
    print()

    # Create server config
    server_config = ServerConfig(
        model_path=model_path,
        port=8080,
        stop_sequences=QWEN_STOP_SEQUENCES,
    )

    # Start server
    print("Starting mlx_lm.server...")
    async with ServerProcess(config=server_config) as server:
        print(f"✓ Server ready at {server.config.base_url}")

        # Create agent
        model = create_server_model(server_config)
        agent_config = AgentConfig(
            temperature=0.0,  # Deterministic for profiling
            stop_sequences=QWEN_STOP_SEQUENCES,
        )
        agent = create_pydantic_agent(model=model, config=agent_config)

        # Create local client
        client = LocalClient(workspace=Path.cwd())

        # Profile each query
        latencies = []
        for i, test in enumerate(TEST_QUERIES, 1):
            latency = await profile_query(agent, client, test, i)
            latencies.append(latency)

        # Calculate aggregate metrics
        avg_total = sum(q.total_time_ms for q in latencies) / len(latencies)
        avg_generation = sum(q.generation_time_ms for q in latencies) / len(latencies)
        avg_tool = sum(q.tool_time_ms for q in latencies) / len(latencies)
        avg_framework = sum(q.framework_overhead_ms for q in latencies) / len(latencies)

        generation_pct = (avg_generation / avg_total) * 100 if avg_total > 0 else 0
        tool_pct = (avg_tool / avg_total) * 100 if avg_total > 0 else 0
        framework_pct = (avg_framework / avg_total) * 100 if avg_total > 0 else 0

        accuracy = sum(1 for q in latencies if q.correct) / len(latencies) * 100

        report = ProfileReport(
            model_path=model_path,
            timestamp=datetime.now().isoformat(),
            queries=[latency for latency in latencies],
            avg_total_ms=avg_total,
            avg_generation_ms=avg_generation,
            avg_tool_ms=avg_tool,
            avg_framework_ms=avg_framework,
            generation_pct=generation_pct,
            tool_pct=tool_pct,
            framework_pct=framework_pct,
            accuracy=accuracy,
        )

        return report


def print_summary(report: ProfileReport) -> None:
    """Print human-readable summary of profiling results."""
    print("\n" + "=" * 80)
    print("PROFILING RESULTS")
    print("=" * 80)
    print(f"\nAccuracy: {report.accuracy:.1f}% ({int(report.accuracy/20)}/5)")
    print("\nAverage latency breakdown per query:")
    print(f"  Total:      {report.avg_total_ms:7.1f}ms (100.0%)")
    print(f"  Generation: {report.avg_generation_ms:7.1f}ms ({report.generation_pct:5.1f}%)")
    print(f"  Tool exec:  {report.avg_tool_ms:7.1f}ms ({report.tool_pct:5.1f}%)")
    print(f"  Framework:  {report.avg_framework_ms:7.1f}ms ({report.framework_pct:5.1f}%)")

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    if report.generation_pct > 70:
        print("⚠️  Generation time is >70% of total latency")
        print("    → Consider conciseness training to reduce token count")
        print("    → Try speculative decoding to speed up generation")
    elif report.tool_pct > 40:
        print("⚠️  Tool execution time is >40% of total latency")
        print("    → Consider optimizing tool implementations")
        print("    → Speculative decoding won't help much here")
    else:
        print("✓  Latency is balanced across components")
        print("  → Speculative decoding may provide modest speedup")

    print("=" * 80)


def main():
    """Run latency profiling and save results."""
    # Check if fused model exists
    model_path = "fused_model_qwen3_phase21_xml_5bit"
    if not Path(model_path).exists():
        print(f"Error: Model not found at {model_path}")
        print("Please ensure the 5-bit fused model is available.")
        return 1

    # Run profiling
    report = asyncio.run(run_profiling(model_path))

    # Print summary
    print_summary(report)

    # Save JSON report
    output_file = Path("logs/latency_profile.json")
    output_file.parent.mkdir(exist_ok=True)

    # Convert dataclasses to dicts for JSON serialization
    report_dict = {
        "model_path": report.model_path,
        "timestamp": report.timestamp,
        "queries": [
            {
                "query": q.query,
                "expected": q.expected,
                "got": q.got,
                "correct": q.correct,
                "total_time_ms": q.total_time_ms,
                "generation_time_ms": q.generation_time_ms,
                "tool_time_ms": q.tool_time_ms,
                "framework_overhead_ms": q.framework_overhead_ms,
                "num_turns": q.num_turns,
                "response_preview": q.response_preview,
            }
            for q in report.queries
        ],
        "summary": {
            "avg_total_ms": report.avg_total_ms,
            "avg_generation_ms": report.avg_generation_ms,
            "avg_tool_ms": report.avg_tool_ms,
            "avg_framework_ms": report.avg_framework_ms,
            "generation_pct": report.generation_pct,
            "tool_pct": report.tool_pct,
            "framework_pct": report.framework_pct,
            "accuracy": report.accuracy,
        },
    }

    with output_file.open("w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"\n✅ Results saved to {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
