"""Zero-shot Code Mode validation for ollama models.

Tests if a model can follow Code Mode stubs without fine-tuning.
Adapts Phase 27's 40-query suite for zero-shot testing.

Usage:
    python scripts/validate_zero_shot_code_mode.py --model devstral
    python scripts/validate_zero_shot_code_mode.py --model qwen3:30b-a3b
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from punie.acp.contrib.tool_calls import ToolCallTracker  # noqa: E402
from punie.agent.deps import ACPDeps  # noqa: E402
from punie.agent.factory import create_local_agent  # noqa: E402


async def test_query(
    agent, client, query: str, category: str, expects_tool_call: bool
) -> tuple[bool, str, float]:
    """Test a single query and return (success, response, time).

    Args:
        agent: PunieAgent instance
        client: LocalClient instance
        query: Query string to test
        category: Category name for logging
        expects_tool_call: Whether this query should trigger tool calls

    Returns:
        (success, response, elapsed_time)
    """
    deps = ACPDeps(
        client_conn=client,
        session_id="validation-session",
        tracker=ToolCallTracker(),
    )

    start = time.time()
    try:
        result = await agent.run(query, deps=deps)
        elapsed = time.time() - start

        response = result.output
        print(f"\n[{category}] Query: {query[:80]}...")
        print(f"Response: {response[:200]}...")
        print(f"Time: {elapsed:.2f}s")

        # Check if tool was called (tracker has internal _calls dict)
        tool_called = len(deps.tracker._calls) > 0

        # Success heuristic:
        # - If we expect tool call: check that tool was called
        # - If we don't expect tool call: check that response is substantial (direct answer)
        if expects_tool_call:
            success = tool_called
            if not success:
                print("  ❌ Expected tool call but got direct answer")
        else:
            success = len(response) > 20 and not tool_called
            if not success:
                print("  ❌ Expected direct answer but got tool call or empty response")

        if success:
            print("  ✅ Correct behavior")

        return success, response, elapsed

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n[{category}] Query: {query[:80]}...")
        print(f"❌ Error: {e}")
        print(f"Time: {elapsed:.2f}s")
        return False, str(e), elapsed


async def run_validation(model_name: str, workspace: Path) -> bool:
    """Run zero-shot validation suite.

    Args:
        model_name: Model name for ollama (e.g., "devstral", "qwen3:30b-a3b")
        workspace: Workspace directory for file operations

    Returns:
        True if overall accuracy >= 50% (zero-shot threshold)
    """
    print("=" * 80)
    print("ZERO-SHOT CODE MODE VALIDATION")
    print("=" * 80)
    print(f"Model: {model_name}")
    print(f"Workspace: {workspace}")
    print("Backend: ollama (assumed running at http://localhost:11434)")
    print("=" * 80)

    # Create agent with ollama model
    print("\nCreating agent...")
    agent, client = create_local_agent(
        model=f"ollama:{model_name}",
        workspace=workspace,
    )

    results = {
        "direct_answers": [],
        "single_tool": [],
        "multi_step": [],
        "field_access": [],
    }

    times = []

    # Category 1: Direct answers (5 queries) - should NOT call tools
    print("\n" + "=" * 80)
    print("Category 1: Direct Answers (expect NO tool calls)")
    print("=" * 80)

    direct_queries = [
        "What's the difference between git merge and git rebase?",
        "When should I use type hints in Python?",
        "What is dependency injection?",
        "Explain the difference between ruff and pytest",
        "What are LSP capabilities?",
    ]

    for query in direct_queries:
        success, response, elapsed = await test_query(
            agent, client, query, "Direct", expects_tool_call=False
        )
        results["direct_answers"].append(success)
        times.append(elapsed)

    # Category 2: Single tool calls (5 queries) - should call tools
    print("\n" + "=" * 80)
    print("Category 2: Single Tool Calls (expect tool calls)")
    print("=" * 80)

    single_tool_queries = [
        "Check for type errors in src/",
        "Run ruff linter on src/punie/",
        "What files have changed? Show git status",
        "Read the README.md file",
        "Run pytest on tests/",
    ]

    for query in single_tool_queries:
        success, response, elapsed = await test_query(
            agent, client, query, "Single Tool", expects_tool_call=True
        )
        results["single_tool"].append(success)
        times.append(elapsed)

    # Category 3: Multi-step Code Mode (5 queries) - should call execute_code
    print("\n" + "=" * 80)
    print("Category 3: Multi-Step Code Mode (expect execute_code)")
    print("=" * 80)

    multi_step_queries = [
        "Find all Python files and count imports",
        "Run full quality check: ruff, pytest, and typecheck",
        "Count staged vs unstaged files using git",
        "List all test files and show their pass rates",
        "Find definition of PunieAgent and show its methods",
    ]

    for query in multi_step_queries:
        success, response, elapsed = await test_query(
            agent, client, query, "Multi-Step", expects_tool_call=True
        )
        results["multi_step"].append(success)
        times.append(elapsed)

    # Category 4: Field access (5 queries) - should access structured results
    print("\n" + "=" * 80)
    print("Category 4: Field Access (expect structured result access)")
    print("=" * 80)

    field_access_queries = [
        "Show only fixable ruff violations",
        "Count passed vs failed tests",
        "Filter type errors by severity",
        "Show git diff statistics with additions and deletions",
        "Count errors vs warnings in type check results",
    ]

    for query in field_access_queries:
        success, response, elapsed = await test_query(
            agent, client, query, "Field Access", expects_tool_call=True
        )
        results["field_access"].append(success)
        times.append(elapsed)

    # Print summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    for category, successes in results.items():
        passed = sum(successes)
        total = len(successes)
        percentage = (passed / total * 100) if total > 0 else 0
        status = "✓" if percentage >= 50 else "✗"  # Lower threshold for zero-shot
        print(f"{status} {category:20s}: {passed}/{total} ({percentage:.0f}%)")

    total_passed = sum(sum(s) for s in results.values())
    total_queries = sum(len(s) for s in results.values())
    overall_percentage = (total_passed / total_queries * 100) if total_queries > 0 else 0

    print(f"\n{'=' * 80}")
    print(f"Overall: {total_passed}/{total_queries} ({overall_percentage:.0f}%)")
    print("Zero-shot target: ≥50% (10/20)")
    print("Fine-tuned baseline: 100% (40/40)")
    print(f"Status: {'✓ PASS' if overall_percentage >= 50 else '✗ FAIL'}")
    print(f"{'=' * 80}")

    # Performance stats
    avg_time = sum(times) / len(times) if times else 0
    print("\nPerformance:")
    print(f"  Average generation time: {avg_time:.2f}s")
    print(f"  Total validation time: {sum(times):.2f}s")

    # Interpretation
    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    if overall_percentage >= 70:
        print("✅ EXCELLENT - Model follows Code Mode stubs very well!")
        print("   Zero-shot performance suggests minimal fine-tuning needed.")
    elif overall_percentage >= 50:
        print("✓ GOOD - Model shows promise with Code Mode stubs.")
        print("  Consider adding fine-tuning to improve field access and multi-step.")
    else:
        print("⚠ NEEDS WORK - Zero-shot performance is low.")
        print("  Options:")
        print("  1. Add fine-tuning examples (Phase 27 approach)")
        print("  2. Promote typed tools to individual PydanticAI tools")
        print("  3. Try a larger model (e.g., 70B instead of 24B)")

    return overall_percentage >= 50


def main():
    parser = argparse.ArgumentParser(
        description="Validate zero-shot Code Mode performance with ollama models"
    )
    parser.add_argument(
        "--model",
        default="devstral",
        help="Ollama model name (e.g., 'devstral', 'qwen3:30b-a3b')",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace directory for file operations",
    )

    args = parser.parse_args()

    # Check if ollama is running
    try:
        import httpx

        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if response.status_code != 200:
            print("❌ Ollama server not responding at http://localhost:11434")
            print("   Start ollama with: ollama serve")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to ollama: {e}")
        print("   Start ollama with: ollama serve")
        sys.exit(1)

    # Run validation
    success = asyncio.run(run_validation(args.model, args.workspace))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
