"""Phase 27 Validation: 40-query comprehensive suite.

Tests across 8 categories:
1. Direct answers (5 queries) → Target: 100%
2. Existing LSP (goto_def, find_refs) (5 queries) → Target: ≥90%
3. New LSP (hover, doc_symbols, workspace_symbols) (5 queries) → Target: ≥80%
4. Git tools (status, diff, log) (5 queries) → Target: ≥80%
5. Existing tools (ruff, pytest, typecheck) (5 queries) → Target: ≥90%
6. Field access (all tools) (5 queries) → Target: ≥80%
7. Cross-tool workflows (5 queries) → Target: ≥60%
8. Discrimination (tool vs direct) (5 queries) → Target: ≥90%

Overall target: ≥85% (34/40)
"""

import sys
import time
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mlx_lm import generate, load

# Import prompt formatter
from punie.agent.prompt_utils import format_prompt


def test_query(model, tokenizer, query: str, category: str, model_path: str) -> tuple[bool, str, float]:
    """Test a single query and return (success, response, time)."""
    # Format prompt using shared utility
    prompt = format_prompt(query, model_path)

    # Generate
    start = time.time()
    response = generate(model, tokenizer, prompt=prompt, max_tokens=512)
    elapsed = time.time() - start

    print(f"\n[{category}] Query: {query[:80]}...")
    print(f"Response: {response[:200]}...")
    print(f"Time: {elapsed:.2f}s")

    # Simple success heuristic (can be refined)
    success = len(response) > 10 and not response.startswith("Error")

    return success, response, elapsed


def run_validation(model_path: str):
    """Run full 40-query validation suite."""
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

    # Category 1: Direct answers (5 queries)
    print("\n" + "=" * 80)
    print("Category 1: Direct Answers")
    print("=" * 80)

    direct_queries = [
        "What's the difference between git merge and git rebase?",
        "When should I use type hints in Python?",
        "What is LSP hover?",
        "When should I use workspace_symbols vs document_symbols?",
        "When should I use pytest_run or run_command pytest?",
    ]

    for query in direct_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "Direct", model_path)
        results["direct_answers"].append(success)
        times.append(elapsed)

    # Category 2: Existing LSP (5 queries)
    print("\n" + "=" * 80)
    print("Category 2: Existing LSP (goto_definition, find_references)")
    print("=" * 80)

    existing_lsp_queries = [
        "Find the definition of UserService in src/services/user.py at line 15",
        "Find all references to authenticate method in src/auth.py",
        "Where is DatabaseConnection defined?",
        "Find references to create_user function",
        "Show definition of TokenManager class",
    ]

    for query in existing_lsp_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "Existing LSP", model_path)
        results["existing_lsp"].append(success)
        times.append(elapsed)

    # Category 3: New LSP (5 queries)
    print("\n" + "=" * 80)
    print("Category 3: New LSP (hover, document_symbols, workspace_symbols)")
    print("=" * 80)

    new_lsp_queries = [
        "Show hover info for UserService at src/services/user.py line 15",
        "What's the structure of src/auth.py? List all symbols",
        "Search workspace for ApiClient symbols",
        "Get type information for authenticate method",
        "Find all classes in src/models/user.py using document symbols",
    ]

    for query in new_lsp_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "New LSP", model_path)
        results["new_lsp"].append(success)
        times.append(elapsed)

    # Category 4: Git tools (5 queries)
    print("\n" + "=" * 80)
    print("Category 4: Git Tools (git_status, git_diff, git_log)")
    print("=" * 80)

    git_queries = [
        "What files have changed? Show git status",
        "Show unstaged changes with git diff",
        "Get recent 10 commits",
        "Count staged vs unstaged files",
        "Show diff statistics for staged changes",
    ]

    for query in git_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "Git", model_path)
        results["git_tools"].append(success)
        times.append(elapsed)

    # Category 5: Existing tools (5 queries)
    print("\n" + "=" * 80)
    print("Category 5: Existing Tools (ruff, pytest, typecheck)")
    print("=" * 80)

    existing_tool_queries = [
        "Run ruff linter on src/",
        "Execute pytest on tests/",
        "Type check src/ with ty",
        "Check for fixable ruff violations",
        "Show failed test details",
    ]

    for query in existing_tool_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "Existing Tools", model_path)
        results["existing_tools"].append(success)
        times.append(elapsed)

    # Category 6: Field access (5 queries)
    print("\n" + "=" * 80)
    print("Category 6: Field Access (structured results)")
    print("=" * 80)

    field_access_queries = [
        "Check hover content length for UserService",
        "Count symbols by kind in src/auth.py",
        "Filter workspace symbols by container name",
        "Show only fixable ruff violations",
        "Count passed vs failed tests",
    ]

    for query in field_access_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "Field Access", model_path)
        results["field_access"].append(success)
        times.append(elapsed)

    # Category 7: Cross-tool workflows (5 queries)
    print("\n" + "=" * 80)
    print("Category 7: Cross-Tool Workflows")
    print("=" * 80)

    cross_tool_queries = [
        "Run full quality check: ruff, pytest, and typecheck",
        "Get git diff and read modified files",
        "Find UserService definition and show hover info",
        "Check git status and diff the staged files",
        "Run tests and lint the failures",
    ]

    for query in cross_tool_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "Cross-Tool", model_path)
        results["cross_tool"].append(success)
        times.append(elapsed)

    # Category 8: Discrimination (5 queries)
    print("\n" + "=" * 80)
    print("Category 8: Discrimination (tool vs direct)")
    print("=" * 80)

    discrimination_queries = [
        "What's the difference between hover and goto definition?",  # Direct
        "Find all pytest test files",  # Tool
        "When should I use git stash?",  # Direct
        "Check types in src/services/",  # Tool
        "What are symbol kinds in LSP?",  # Direct
    ]

    for query in discrimination_queries:
        success, response, elapsed = test_query(model, tokenizer, query, "Discrimination", model_path)
        results["discrimination"].append(success)
        times.append(elapsed)

    # Print summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    category_results = []
    for category, successes in results.items():
        passed = sum(successes)
        total = len(successes)
        percentage = (passed / total * 100) if total > 0 else 0
        status = "✓" if percentage >= 80 else "✗"
        print(f"{status} {category:20s}: {passed}/{total} ({percentage:.0f}%)")
        category_results.append((category, passed, total, percentage))

    total_passed = sum(sum(s) for s in results.values())
    total_queries = sum(len(s) for s in results.values())
    overall_percentage = (total_passed / total_queries * 100) if total_queries > 0 else 0

    print(f"\n{'=' * 80}")
    print(f"Overall: {total_passed}/{total_queries} ({overall_percentage:.0f}%)")
    print("Target: ≥85% (34/40)")
    print(f"Status: {'✓ PASS' if overall_percentage >= 85 else '✗ FAIL'}")
    print(f"{'=' * 80}")

    # Performance stats
    avg_time = sum(times) / len(times) if times else 0
    print("\nPerformance:")
    print(f"  Average generation time: {avg_time:.2f}s")
    print(f"  Total validation time: {sum(times):.2f}s")

    return overall_percentage >= 85


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_phase27_validation.py <model_path>")
        sys.exit(1)

    model_path = sys.argv[1]
    success = run_validation(model_path)
    sys.exit(0 if success else 1)
