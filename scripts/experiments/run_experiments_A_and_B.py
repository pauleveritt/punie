#!/usr/bin/env python3
"""Run Experiments A & B: Validate 30B models

BEFORE RUNNING: Close other apps to free up RAM (need ~20GB available)

Experiment A: Validate Qwen3-30B on 5 real tasks
Experiment B: Compare Qwen2.5-32B vs Qwen3-30B

Total time: ~20-30 minutes
RAM usage: ~16GB peak
"""

import asyncio
from pathlib import Path

from test_30b_real_tasks import REAL_TASKS, test_task, main as run_30b_suite


async def run_experiment_A():
    """Experiment A: Validate Qwen3-30B thoroughly."""
    print("\n" + "=" * 80)
    print("EXPERIMENT A: Validate Qwen3-30B on 5 Real Tasks")
    print("=" * 80)
    print("\nThis will:")
    print("  - Load Qwen3-Coder-30B-A3B-Instruct-4bit")
    print("  - Run 5 diverse codebase tasks")
    print("  - Measure success rate, speed, tool usage")
    print("  - Establish baseline for comparison")
    print("\nExpected time: ~10-12 minutes")
    print("Expected RAM: ~16GB\n")

    input("Press Enter to start Experiment A (or Ctrl+C to cancel)...")

    # Run the existing 30B test suite
    await run_30b_suite()

    print("\n✅ Experiment A complete!")
    print("Results saved to: /tmp/30b_real_tasks_results.txt")


async def run_experiment_B():
    """Experiment B: Compare Qwen2.5-32B vs Qwen3-30B."""
    print("\n" + "=" * 80)
    print("EXPERIMENT B: Compare Qwen2.5-32B vs Qwen3-30B")
    print("=" * 80)
    print("\nThis will:")
    print("  - Test Qwen2.5-Coder-32B-Instruct-4bit")
    print("  - Run Protocol search task (our benchmark)")
    print("  - Compare to Qwen3-30B results")
    print("  - Identify which model is better 'teacher'")
    print("\nExpected time: ~5-7 minutes")
    print("Expected RAM: ~16-18GB\n")

    input("Press Enter to start Experiment B (or Ctrl+C to cancel)...")

    # Import needed modules
    from punie.agent.factory import create_pydantic_agent, create_server_model
    from punie.agent.config import AgentConfig
    from punie.agent.deps import ACPDeps
    from punie.acp.contrib.tool_calls import ToolCallTracker
    from punie.training.server_config import ServerConfig
    from punie.training.server import ServerProcess
    from punie.local import LocalClient
    import time

    workspace = Path.cwd()

    # Test Protocol search on Qwen2.5-32B
    print("\nTesting Qwen2.5-Coder-32B...")

    server_config = ServerConfig(
        model_path="mlx-community/Qwen2.5-Coder-32B-Instruct-4bit",
        port=8082,
    )

    server = ServerProcess(config=server_config)

    try:
        print("Starting server (may take 2-3 minutes)...")
        await server.start(timeout=180.0)
        print("✅ Server started")

        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)
        client = LocalClient(workspace=workspace)

        # Warmup
        print("Warming up...")
        warmup_tracker = ToolCallTracker()
        warmup_deps = ACPDeps(client_conn=client, session_id="warmup", tracker=warmup_tracker)
        await agent.run("What is 2+2?", deps=warmup_deps)

        # Protocol search task
        task = {
            "id": "protocol_search",
            "question": "Which classes in this codebase subclass from Protocol?",
            "expected_concepts": ["HttpAppFactory", "Client", "Agent", "MessageDispatcher"],
        }

        result = await test_task(agent, client, task)

        print("\n" + "=" * 80)
        print("QWEN2.5-32B RESULTS")
        print("=" * 80)
        print(f"Success: {result['success']}")
        print(f"Time: {result['time']:.2f}s")
        print(f"Tool calls: {result['tool_calls']}")
        print(f"Concepts found: {result['found_concepts']}/{result['total_concepts']}")

        # Save results
        with open("qwen25_32b_protocol_results.txt", "w") as f:
            f.write("Qwen2.5-Coder-32B Protocol Search Results\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Success: {result['success']}\n")
            f.write(f"Time: {result['time']:.2f}s\n")
            f.write(f"Tool calls: {result['tool_calls']}\n")
            f.write(f"Concepts: {result['found_concepts']}/{result['total_concepts']}\n")

    finally:
        await server.stop()

    print("\n✅ Experiment B complete!")
    print("Results saved to: qwen25_32b_protocol_results.txt")

    # Compare to Qwen3-30B
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print("\nQwen2.5-32B vs Qwen3-30B (from previous test):")
    print(f"\n{'Model':<25} {'Time':<12} {'Tools':<10} {'Success':<10}")
    print("-" * 57)

    time_str = f"{result['time']:.2f}s"
    print(f"{'Qwen2.5-32B (new)':<25} {time_str:<12} {result['tool_calls']:<10} {result['success']}")
    print(f"{'Qwen3-30B (previous)':<25} {'93.49s':<12} {'6':<10} {'True'}")

    if result['time'] < 93.49:
        speedup = 93.49 / result['time']
        print(f"\n🚀 Qwen2.5-32B is {speedup:.2f}x FASTER!")

    if result['success']:
        print("✅ Both models have autonomous reasoning")
        print("\nRecommendation: Use the faster model as 'teacher' for distillation")


async def main():
    """Run both experiments sequentially."""
    print("=" * 80)
    print("EXPERIMENT SUITE: Validate and Compare 30B Models")
    print("=" * 80)
    print("\n⚠️  IMPORTANT: Close other apps first!")
    print("   These tests need ~20GB free RAM")
    print("   Check Activity Monitor and close memory-heavy apps\n")

    input("Press Enter when ready to begin (or Ctrl+C to exit)...")

    try:
        # Run Experiment A (full validation)
        await run_experiment_A()

        print("\n" + "=" * 80)
        print("Experiment A complete. Take a break before Experiment B?")
        print("=" * 80)
        choice = input("Continue to Experiment B? (y/n): ")

        if choice.lower() == 'y':
            # Run Experiment B (comparison)
            await run_experiment_B()

            print("\n" + "=" * 80)
            print("🎉 ALL EXPERIMENTS COMPLETE!")
            print("=" * 80)
            print("\nResults:")
            print("  - Experiment A: /tmp/30b_real_tasks_results.txt")
            print("  - Experiment B: qwen25_32b_protocol_results.txt")
            print("\nNext steps:")
            print("  1. Review results to pick best 'teacher' model")
            print("  2. Begin data generation for knowledge distillation")
            print("  3. Or explore 14B models if 32B shows promise")
        else:
            print("\n⏸️  Experiment B skipped. Run later with:")
            print("   uv run python run_experiments_A_and_B.py")

    except KeyboardInterrupt:
        print("\n\n⏸️  Experiments cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
