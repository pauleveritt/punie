#!/usr/bin/env python3
"""Test 30B model on multiple real codebase tasks."""

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


REAL_TASKS = [
    {
        "id": "protocol_search",
        "question": "Which classes in this codebase subclass from Protocol?",
        "expected_concepts": ["HttpAppFactory", "Client", "Agent", "MessageDispatcher"],
    },
    {
        "id": "import_usage",
        "question": "Find all files that import 'asyncio' and list them",
        "expected_concepts": ["asyncio", "import", ".py files"],
    },
    {
        "id": "function_signature",
        "question": "What are the parameters for the create_pydantic_agent function?",
        "expected_concepts": ["model", "config", "toolsets"],
    },
    {
        "id": "test_count",
        "question": "How many test files are in the tests/ directory?",
        "expected_concepts": ["tests/", "test_", ".py"],
    },
    {
        "id": "dataclass_search",
        "question": "List all dataclasses defined in src/punie/training/",
        "expected_concepts": ["@dataclass", "frozen=True"],
    },
]


async def test_task(agent, client, task):
    """Run a single task and measure performance."""
    tracker = ToolCallTracker()
    deps = ACPDeps(
        client_conn=client,
        session_id=f"task-{task['id']}",
        tracker=tracker,
    )

    print(f"\n{'=' * 80}")
    print(f"TASK: {task['id']}")
    print(f"{'=' * 80}")
    print(f"Question: {task['question']}")

    start = time.perf_counter()
    try:
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

        # Check if expected concepts are in response
        response_lower = result.output.lower()
        found_concepts = [
            concept for concept in task['expected_concepts']
            if concept.lower() in response_lower
        ]

        success = len(found_concepts) > 0

        print(f"\nResponse ({elapsed:.2f}s, {len(tool_calls)} tool calls):")
        print(f"{result.output[:500]}...")  # First 500 chars
        print(f"\nExpected concepts found: {found_concepts}")
        print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")

        return {
            "id": task['id'],
            "success": success,
            "time": elapsed,
            "tool_calls": len(tool_calls),
            "found_concepts": len(found_concepts),
            "total_concepts": len(task['expected_concepts']),
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"\n❌ ERROR ({elapsed:.2f}s): {e}")
        return {
            "id": task['id'],
            "success": False,
            "time": elapsed,
            "tool_calls": 0,
            "found_concepts": 0,
            "total_concepts": len(task['expected_concepts']),
            "error": str(e),
        }


async def main():
    """Test 30B on multiple real codebase tasks."""
    print("=" * 80)
    print("30B MODEL: Real Task Testing Suite")
    print("=" * 80)

    model_path = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8080,
    )

    print("\nStarting server...")
    server = ServerProcess(config=server_config)
    await server.start()

    try:
        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)
        client = LocalClient(workspace=workspace)

        # Warmup
        print("\nWarming up...")
        warmup_tracker = ToolCallTracker()
        warmup_deps = ACPDeps(client_conn=client, session_id="warmup", tracker=warmup_tracker)
        await agent.run("What is 2+2?", deps=warmup_deps)
        print("Ready!")

        # Run all tasks
        results = []
        for task in REAL_TASKS:
            result = await test_task(agent, client, task)
            results.append(result)

        # Summary
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")

        total_tasks = len(results)
        successful = sum(1 for r in results if r['success'])
        total_time = sum(r['time'] for r in results)
        total_tool_calls = sum(r['tool_calls'] for r in results)
        avg_time = total_time / total_tasks if total_tasks > 0 else 0

        print(f"\nTasks completed: {successful}/{total_tasks} ({successful/total_tasks*100:.1f}%)")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time per task: {avg_time:.2f}s")
        print(f"Total tool calls: {total_tool_calls}")
        print(f"Average tool calls per task: {total_tool_calls/total_tasks:.1f}")

        print(f"\nPer-task breakdown:")
        for r in results:
            status = "✅" if r['success'] else "❌"
            concepts = f"{r['found_concepts']}/{r['total_concepts']}"
            print(f"  {status} {r['id']}: {r['time']:.2f}s, {r['tool_calls']} calls, {concepts} concepts")

        # Save results
        with open("/tmp/30b_real_tasks_results.txt", "w") as f:
            f.write(f"30B Real Task Testing Results\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(f"Success rate: {successful}/{total_tasks} ({successful/total_tasks*100:.1f}%)\n")
            f.write(f"Average time: {avg_time:.2f}s\n")
            f.write(f"Average tool calls: {total_tool_calls/total_tasks:.1f}\n\n")
            for r in results:
                f.write(f"{r['id']}: {'SUCCESS' if r['success'] else 'FAILED'}\n")

    finally:
        print("\nStopping server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
