"""Phase 27 Semantic Validation: Checks if model uses CORRECT tools, not just any output.

This replaces the broken validation that used `len(response) > 10`.

Tests across 8 categories:
1. Direct answers (5 queries) → Target: 100% - No tool calls
2. Existing LSP (goto_def, find_refs) (5 queries) → Target: ≥90% - Correct tool used
3. New LSP (hover, doc_symbols, workspace_symbols) (5 queries) → Target: ≥80% - Correct tool used
4. Git tools (status, diff, log) (5 queries) → Target: ≥80% - Correct tool used
5. Existing tools (ruff, pytest, typecheck) (5 queries) → Target: ≥90% - Correct tool used
6. Field access (all tools) (5 queries) → Target: ≥80% - Correct tool AND field access
7. Cross-tool workflows (5 queries) → Target: ≥60% - Multiple correct tools
8. Discrimination (tool vs direct) (5 queries) → Target: ≥90% - Correct decision

Overall target: ≥75% (30/40) - Realistic after fixing training data
"""

import sys
import time
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mlx_lm import generate, load

# Import prompt formatter (CRITICAL: Always use this, never manual formatting!)
from punie.agent.prompt_utils import format_prompt


def check_tool_in_response(response: str, tool_names: list[str]) -> bool:
    """Check if at least one of the expected tools was called in the response."""
    for tool in tool_names:
        if f"{tool}(" in response:
            return True
    return False


def check_no_tool_call(response: str) -> bool:
    """Check that response is a direct answer (no tool calls)."""
    return "<tool_call>" not in response and "execute_code" not in response


def check_field_access(response: str, tool_names: list[str], field_names: list[str]) -> bool:
    """Check that response calls correct tool AND accesses expected fields."""
    has_tool = check_tool_in_response(response, tool_names)
    has_fields = any(f"result.{field}" in response for field in field_names)
    return has_tool and has_fields


def test_query(
    model,
    tokenizer,
    query: str,
    category: str,
    model_path: str,
    check_fn,
    check_args: tuple = (),
) -> tuple[bool, str, float]:
    """Test a single query with a semantic check function.

    Args:
        model: MLX model
        tokenizer: MLX tokenizer
        query: User query string
        category: Category name for logging
        model_path: Path to model (for prompt formatting)
        check_fn: Function to check if response is correct
        check_args: Additional arguments for check_fn (e.g., expected tool names)

    Returns:
        (success, response, elapsed_time)
    """
    # Format prompt using shared utility (CRITICAL for train/test consistency)
    prompt = format_prompt(query, model_path)

    # Generate
    start = time.time()
    response = generate(model, tokenizer, prompt=prompt, max_tokens=512)
    elapsed = time.time() - start

    print(f"\n[{category}] Query: {query[:80]}...")
    print(f"Response: {response[:200]}...")
    print(f"Time: {elapsed:.2f}s")

    # Apply semantic check
    success = check_fn(response, *check_args)

    if not success:
        print("❌ FAILED semantic check")
    else:
        print("✅ PASSED semantic check")

    return success, response, elapsed


def run_validation(model_path: str):
    """Run full 40-query semantic validation suite."""
    print(f"Loading model from {model_path}...")
    model, tokenizer = load(model_path)

    results = {
        "direct_answers": [],
        "existing_lsp": [],
        "new_lsp": [],
        "git_tools": [],
        "existing_tools": [],
        "field_access": [],
        "cross_tool": [],
        "discrimination": [],
    }

    times = []

    # Category 1: Direct answers (5 queries) - NO tool calls expected
    print("\n" + "=" * 80)
    print("Category 1: Direct Answers (no tool calls)")
    print("=" * 80)

    direct_queries = [
        "What's the difference between git merge and git rebase?",
        "When should I use type hints in Python?",
        "What is LSP hover?",
        "When should I use workspace_symbols vs document_symbols?",
        "When should I use pytest_run or run_command pytest?",
    ]

    for query in direct_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Direct", model_path, check_no_tool_call
        )
        results["direct_answers"].append(success)
        times.append(elapsed)

    # Category 2: Existing LSP (5 queries) - goto_definition or find_references
    print("\n" + "=" * 80)
    print("Category 2: Existing LSP (goto_definition, find_references)")
    print("=" * 80)

    existing_lsp_queries = [
        ("Find the definition of UserService in src/services/user.py at line 15", ["goto_definition"]),
        ("Find all references to authenticate method in src/auth.py", ["find_references"]),
        ("Where is DatabaseConnection defined?", ["goto_definition"]),
        ("Find references to create_user function", ["find_references"]),
        ("Show definition of TokenManager class", ["goto_definition"]),
    ]

    for query, expected_tools in existing_lsp_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Existing LSP", model_path,
            check_tool_in_response, (expected_tools,)
        )
        results["existing_lsp"].append(success)
        times.append(elapsed)

    # Category 3: New LSP (5 queries) - hover, document_symbols, workspace_symbols
    print("\n" + "=" * 80)
    print("Category 3: New LSP (hover, document_symbols, workspace_symbols)")
    print("=" * 80)

    new_lsp_queries = [
        ("Show hover info for UserService at src/services/user.py line 15", ["hover"]),
        ("What's the structure of src/auth.py? List all symbols", ["document_symbols"]),
        ("Search workspace for ApiClient symbols", ["workspace_symbols"]),
        ("Get type information for authenticate method", ["hover", "goto_definition"]),  # Either is acceptable
        ("Find all classes in src/models/user.py using document symbols", ["document_symbols"]),
    ]

    for query, expected_tools in new_lsp_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "New LSP", model_path,
            check_tool_in_response, (expected_tools,)
        )
        results["new_lsp"].append(success)
        times.append(elapsed)

    # Category 4: Git tools (5 queries) - git_status, git_diff, git_log
    print("\n" + "=" * 80)
    print("Category 4: Git Tools (git_status, git_diff, git_log)")
    print("=" * 80)

    git_queries = [
        ("What files have changed? Show git status", ["git_status"]),
        ("Show unstaged changes with git diff", ["git_diff"]),
        ("Get recent 10 commits", ["git_log"]),
        ("Count staged vs unstaged files", ["git_status"]),
        ("Show diff statistics for staged changes", ["git_diff"]),
    ]

    for query, expected_tools in git_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Git", model_path,
            check_tool_in_response, (expected_tools,)
        )
        results["git_tools"].append(success)
        times.append(elapsed)

    # Category 5: Existing tools (5 queries) - ruff_check, pytest_run, typecheck
    print("\n" + "=" * 80)
    print("Category 5: Existing Tools (ruff_check, pytest_run, typecheck)")
    print("=" * 80)

    existing_tool_queries = [
        ("Run ruff linter on src/", ["ruff_check"]),
        ("Execute pytest on tests/", ["pytest_run"]),
        ("Type check src/ with ty", ["typecheck"]),
        ("Check for fixable ruff violations", ["ruff_check"]),
        ("Show failed test details", ["pytest_run"]),
    ]

    for query, expected_tools in existing_tool_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Existing Tools", model_path,
            check_tool_in_response, (expected_tools,)
        )
        results["existing_tools"].append(success)
        times.append(elapsed)

    # Category 6: Field access (5 queries) - Tool + structured field access
    print("\n" + "=" * 80)
    print("Category 6: Field Access (tool + result.field)")
    print("=" * 80)

    field_access_queries = [
        ("Check hover content length for UserService", ["hover"], ["content", "success"]),
        ("Count symbols by kind in src/auth.py", ["document_symbols"], ["symbols", "kind"]),
        ("Filter workspace symbols by container name", ["workspace_symbols"], ["symbols", "container_name"]),
        ("Show only fixable ruff violations", ["ruff_check"], ["violations", "fixable"]),
        ("Count passed vs failed tests", ["pytest_run"], ["passed", "failed"]),
    ]

    for query, expected_tools, expected_fields in field_access_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Field Access", model_path,
            check_field_access, (expected_tools, expected_fields)
        )
        results["field_access"].append(success)
        times.append(elapsed)

    # Category 7: Cross-tool workflows (5 queries) - Multiple tools
    print("\n" + "=" * 80)
    print("Category 7: Cross-Tool Workflows")
    print("=" * 80)

    cross_tool_queries = [
        ("Run full quality check: ruff, pytest, and typecheck", ["ruff_check", "pytest_run", "typecheck"]),
        ("Get git diff and read modified files", ["git_diff", "read_file"]),
        ("Find UserService definition and show hover info", ["goto_definition", "hover"]),
        ("Check git status and diff the staged files", ["git_status", "git_diff"]),
        ("Run tests and lint the failures", ["pytest_run", "ruff_check"]),
    ]

    for query, expected_tools in cross_tool_queries:
        # For cross-tool, we check if ANY of the expected tools appear (not all required)
        success, response, elapsed = test_query(
            model, tokenizer, query, "Cross-Tool", model_path,
            check_tool_in_response, (expected_tools,)
        )
        results["cross_tool"].append(success)
        times.append(elapsed)

    # Category 8: Discrimination (5 queries) - Mix of tool vs direct
    print("\n" + "=" * 80)
    print("Category 8: Discrimination (tool vs direct)")
    print("=" * 80)

    discrimination_queries = [
        ("What's the difference between hover and goto definition?", check_no_tool_call, ()),
        ("Find all pytest test files", check_tool_in_response, (["grep", "run_command"],)),
        ("When should I use git stash?", check_no_tool_call, ()),
        ("Check types in src/services/", check_tool_in_response, (["typecheck"],)),
        ("What are symbol kinds in LSP?", check_no_tool_call, ()),
    ]

    for query, check_fn, check_args in discrimination_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Discrimination", model_path,
            check_fn, check_args
        )
        results["discrimination"].append(success)
        times.append(elapsed)

    # Print summary
    print("\n" + "=" * 80)
    print("SEMANTIC VALIDATION SUMMARY")
    print("=" * 80)

    category_results = []
    for category, successes in results.items():
        passed = sum(successes)
        total = len(successes)
        percentage = (passed / total * 100) if total > 0 else 0

        # Determine target based on category
        targets = {
            "direct_answers": 100,
            "existing_lsp": 90,
            "new_lsp": 80,
            "git_tools": 80,
            "existing_tools": 90,
            "field_access": 80,
            "cross_tool": 60,
            "discrimination": 90,
        }
        target = targets.get(category, 80)
        status = "✓" if percentage >= target else "✗"

        print(f"{status} {category:20s}: {passed}/{total} ({percentage:.0f}%) [target: {target}%]")
        category_results.append((category, passed, total, percentage))

    total_passed = sum(sum(s) for s in results.values())
    total_queries = sum(len(s) for s in results.values())
    overall_percentage = (total_passed / total_queries * 100) if total_queries > 0 else 0

    print(f"\n{'=' * 80}")
    print(f"Overall: {total_passed}/{total_queries} ({overall_percentage:.0f}%)")
    print("Target: ≥75% (30/40) - Realistic baseline after audit")
    print(f"Status: {'✓ PASS' if overall_percentage >= 75 else '✗ FAIL'}")
    print(f"{'=' * 80}")

    # Performance stats
    avg_time = sum(times) / len(times) if times else 0
    print("\nPerformance:")
    print(f"  Average generation time: {avg_time:.2f}s")
    print(f"  Total validation time: {sum(times):.2f}s")

    return overall_percentage >= 75


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_phase27_semantic_validation.py <model_path>")
        sys.exit(1)

    model_path = sys.argv[1]
    success = run_validation(model_path)
    sys.exit(0 if success else 1)
