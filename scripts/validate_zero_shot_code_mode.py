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

from pydantic_ai.messages import ModelResponse, ToolCallPart  # noqa: E402

from punie.acp.contrib.tool_calls import ToolCallTracker  # noqa: E402
from punie.agent.deps import ACPDeps  # noqa: E402
from punie.agent.factory import create_local_agent  # noqa: E402


async def test_query(
    agent, client, query: str, category: str, expected_tool: str | None = None
) -> tuple[bool, str, float]:
    """Test a single query and return (success, response, time).

    Args:
        agent: PunieAgent instance
        client: LocalClient instance
        query: Query string to test
        category: Category name for logging
        expected_tool: Expected tool name (None for direct answers)

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

        # Collect all tool calls from message history
        tools_called = [
            part.tool_name
            for msg in result.all_messages()
            if isinstance(msg, ModelResponse)
            for part in msg.parts
            if isinstance(part, ToolCallPart)
        ]

        tool_call_count = len(tools_called)
        print(f"  Tool calls: {tool_call_count} (1 = first-call success, >1 = retries)")
        if tools_called:
            print(f"  Tools used: {', '.join(tools_called)}")

        # Success check:
        # - If expected_tool is None: check that no tools were called (direct answer)
        # - If expected_tool is specified: check that the specific tool was called
        if expected_tool is None:
            # Direct answer expected
            success = len(tools_called) == 0 and len(response) > 20
            if not success:
                if tools_called:
                    print(f"  ❌ Expected direct answer but got tool calls: {tools_called}")
                else:
                    print("  ❌ Expected direct answer but response too short")
        else:
            # Tool call expected
            success = expected_tool in tools_called
            if not success:
                print(f"  ❌ Expected {expected_tool}, got: {tools_called or 'no tools'}")

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
            agent, client, query, "Direct", expected_tool=None
        )
        results["direct_answers"].append(success)
        times.append(elapsed)

    # Category 2: Single tool calls (5 queries) - should call direct tools
    print("\n" + "=" * 80)
    print("Category 2: Single Tool Calls (expect tool calls)")
    print("=" * 80)

    single_tool_queries = [
        ("Check for type errors in src/", "typecheck_direct"),
        ("Run ruff linter on src/punie/", "ruff_check_direct"),
        ("What files have changed? Show git status", "git_status_direct"),
        ("Read the README.md file", "read_file"),
        ("Run pytest on tests/", "pytest_run_direct"),
    ]

    for query, expected_tool in single_tool_queries:
        success, response, elapsed = await test_query(
            agent, client, query, "Single Tool", expected_tool=expected_tool
        )
        results["single_tool"].append(success)
        times.append(elapsed)

    # Category 3: Multi-step (5 queries) - should call multiple tools across turns
    # For multi-step, we check if ANY appropriate tool was called (flexible)
    print("\n" + "=" * 80)
    print("Category 3: Multi-Step (expect multiple tool calls)")
    print("=" * 80)

    multi_step_queries = [
        ("Find all Python files and count imports", "read_file"),
        ("Run full quality check: ruff, pytest, and typecheck", "ruff_check_direct"),
        ("Count staged vs unstaged files using git", "git_status_direct"),
        ("List all test files and show their pass rates", "pytest_run_direct"),
        ("Find definition of PunieAgent and show its methods", "goto_definition_direct"),
    ]

    for query, expected_tool in multi_step_queries:
        success, response, elapsed = await test_query(
            agent, client, query, "Multi-Step", expected_tool=expected_tool
        )
        results["multi_step"].append(success)
        times.append(elapsed)

    # Category 4: Field access (4 queries) - direct tools return structured text
    print("\n" + "=" * 80)
    print("Category 4: Field Access (expect structured result parsing)")
    print("=" * 80)

    field_access_queries = [
        ("Show only fixable ruff violations", "ruff_check_direct"),
        ("Count passed vs failed tests", "pytest_run_direct"),
        ("Filter type errors by severity", "typecheck_direct"),
        ("Show git diff statistics with additions and deletions", "git_diff_direct"),
    ]

    for query, expected_tool in field_access_queries:
        success, response, elapsed = await test_query(
            agent, client, query, "Field Access", expected_tool=expected_tool
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
