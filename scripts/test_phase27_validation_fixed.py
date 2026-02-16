#!/usr/bin/env python3
"""Phase 27.5 Validation Suite - FIXED VERSION

This version actually checks if tools are called correctly, not just len(response) > 10.

Key fixes:
1. Check if specific tools are called (not just "response exists")
2. For cross-tool queries, check if ALL expected tools are called (not just ANY)
3. For discrimination queries, check tool presence vs absence
4. For field access queries, check if result fields are accessed

This should give us honest accuracy numbers.
"""

import sys
import time
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from punie.agent.prompt_utils import format_prompt
from mlx_lm import generate, load


def check_tool_called(response: str, tool_name: str) -> bool:
    """Check if a specific tool was called."""
    # Look for function call pattern: tool_name(
    return f"{tool_name}(" in response


def check_all_tools_called(response: str, tool_names: list[str]) -> bool:
    """Check if ALL expected tools were called (for cross-tool queries)."""
    return all(check_tool_called(response, tool) for tool in tool_names)


def check_no_tool_call(response: str) -> bool:
    """Check that response is direct answer, not a tool call."""
    # Common tool indicators
    tool_indicators = [
        "execute_code(",
        "result = ",
        "typecheck(",
        "ruff_check(",
        "pytest_run(",
        "git_status(",
        "git_diff(",
        "git_log(",
        "goto_definition(",
        "find_references(",
        "hover(",
        "document_symbols(",
        "workspace_symbols(",
        "read_file(",
        "write_file(",
        "run_command(",
    ]

    return not any(indicator in response for indicator in tool_indicators)


def check_field_access(response: str, fields: list[str]) -> bool:
    """Check if result fields are accessed (e.g., result.errors, result.error_count)."""
    # Look for field access patterns: result.field_name or .field_name
    return any(f".{field}" in response for field in fields)


def test_query(
    model,
    tokenizer,
    query: str,
    category: str,
    model_path: str,
    *,
    expect_tools: list[str] | None = None,
    expect_no_tools: bool = False,
    expect_all_tools: bool = False,
    expect_fields: list[str] | None = None,
) -> tuple[bool, str, float]:
    """Test a single query with proper validation.

    Args:
        model: The model to test
        tokenizer: The tokenizer
        query: Query string
        category: Category name for logging
        model_path: Path to model (for prompt formatting)
        expect_tools: List of tools that should be called (checks ANY by default)
        expect_no_tools: True if query should NOT call any tools (direct answer)
        expect_all_tools: True if ALL tools in expect_tools must be called (cross-tool)
        expect_fields: List of fields that should be accessed (e.g., ["errors", "error_count"])

    Returns:
        (success, response, elapsed_time)
    """
    # Format prompt using shared utility
    prompt = format_prompt(query, model_path)

    # Generate
    start = time.time()
    response = generate(model, tokenizer, prompt=prompt, max_tokens=512)
    elapsed = time.time() - start

    print(f"\n[{category}] Query: {query[:80]}...")
    print(f"Response: {response[:300]}...")

    # Validate based on expectations
    success = True

    if expect_no_tools:
        # Direct answer - should NOT call tools
        if not check_no_tool_call(response):
            print("  ❌ FAIL: Called tool when should give direct answer")
            success = False
        else:
            print("  ✅ PASS: Direct answer (no tool call)")

    elif expect_tools:
        if expect_all_tools:
            # Cross-tool workflow - ALL tools must be called
            if not check_all_tools_called(response, expect_tools):
                called = [t for t in expect_tools if check_tool_called(response, t)]
                print(f"  ❌ FAIL: Expected ALL {expect_tools}, got only {called}")
                success = False
            else:
                print(f"  ✅ PASS: Called all tools {expect_tools}")
        else:
            # Single/multi-tool - ANY of the expected tools is OK
            if not any(check_tool_called(response, tool) for tool in expect_tools):
                print(f"  ❌ FAIL: Expected one of {expect_tools}, got none")
                success = False
            else:
                called = [t for t in expect_tools if check_tool_called(response, t)]
                print(f"  ✅ PASS: Called {called}")

    if expect_fields:
        # Field access - check if result fields are accessed
        if not check_field_access(response, expect_fields):
            print(f"  ❌ FAIL: Expected to access fields {expect_fields}")
            success = False
        else:
            print("  ✅ PASS: Accessed result fields")

    # Fallback: if no expectations, just check it's not empty/error
    if not expect_no_tools and not expect_tools and not expect_fields:
        if len(response) < 10 or response.startswith("Error"):
            print("  ❌ FAIL: Empty or error response")
            success = False
        else:
            print("  ✅ PASS: Non-empty response")

    print(f"Time: {elapsed:.2f}s")

    return success, response, elapsed


def run_validation(model_path: str):
    """Run full 40-query validation suite with HONEST checking."""
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
    print("Category 1: Direct Answers (NO tools should be called)")
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
            model, tokenizer, query, "Direct Answer", model_path, expect_no_tools=True
        )
        results["direct_answers"].append(success)
        times.append(elapsed)

    # Category 2: Existing LSP (5 queries)
    print("\n" + "=" * 80)
    print("Category 2: Existing LSP (goto_definition, find_references)")
    print("=" * 80)

    existing_lsp_queries = [
        ("Find definition of UserService", ["goto_definition"]),
        ("Find all references to process_data", ["find_references"]),
        ("Where is LSPClient defined?", ["goto_definition"]),
        ("Show references to execute_code", ["find_references"]),
        ("Goto definition of TypeChecker", ["goto_definition"]),
    ]

    for query, tools in existing_lsp_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Existing LSP", model_path, expect_tools=tools
        )
        results["existing_lsp"].append(success)
        times.append(elapsed)

    # Category 3: New LSP (5 queries)
    print("\n" + "=" * 80)
    print("Category 3: New LSP (hover, document_symbols, workspace_symbols)")
    print("=" * 80)

    new_lsp_queries = [
        ("Show hover info for execute_code", ["hover"]),
        ("List all symbols in typed_tools.py", ["document_symbols"]),
        ("Search workspace for GitStatusResult", ["workspace_symbols"]),
        ("Get hover for LSPClient", ["hover"]),
        ("Show document symbols for lsp_client.py", ["document_symbols"]),
    ]

    for query, tools in new_lsp_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "New LSP", model_path, expect_tools=tools
        )
        results["new_lsp"].append(success)
        times.append(elapsed)

    # Category 4: Git tools (5 queries)
    print("\n" + "=" * 80)
    print("Category 4: Git tools (status, diff, log)")
    print("=" * 80)

    git_queries = [
        ("Show git status", ["git_status"]),
        ("Get git diff for staged files", ["git_diff"]),
        ("Show last 5 commits", ["git_log"]),
        ("Check uncommitted changes", ["git_status", "git_diff"]),
        ("Show recent commit history", ["git_log"]),
    ]

    for query, tools in git_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Git Tools", model_path, expect_tools=tools
        )
        results["git_tools"].append(success)
        times.append(elapsed)

    # Category 5: Existing tools (5 queries)
    print("\n" + "=" * 80)
    print("Category 5: Existing tools (ruff, pytest, typecheck)")
    print("=" * 80)

    existing_tool_queries = [
        ("Run ruff linter", ["ruff_check"]),
        ("Check types with ty", ["typecheck"]),
        ("Run pytest tests", ["pytest_run"]),
        ("Lint with ruff", ["ruff_check"]),
        ("Type check the codebase", ["typecheck"]),
    ]

    for query, tools in existing_tool_queries:
        success, response, elapsed = test_query(
            model, tokenizer, query, "Existing Tools", model_path, expect_tools=tools
        )
        results["existing_tools"].append(success)
        times.append(elapsed)

    # Category 6: Field access (5 queries)
    print("\n" + "=" * 80)
    print("Category 6: Field access (result.errors, result.error_count, etc.)")
    print("=" * 80)

    field_access_queries = [
        ("Check types and show error count", ["typecheck"], ["errors", "error_count"]),
        ("Run ruff and list violations", ["ruff_check"], ["violations", "violation_count"]),
        ("Run tests and show failures", ["pytest_run"], ["failed", "tests"]),
        ("Get git status and count files", ["git_status"], ["files", "file_count"]),
        ("Run typecheck and iterate errors", ["typecheck"], ["errors"]),
    ]

    for query, tools, fields in field_access_queries:
        success, response, elapsed = test_query(
            model,
            tokenizer,
            query,
            "Field Access",
            model_path,
            expect_tools=tools,
            expect_fields=fields,
        )
        results["field_access"].append(success)
        times.append(elapsed)

    # Category 7: Cross-tool workflows (5 queries) - **FIXED: Check ALL tools**
    print("\n" + "=" * 80)
    print("Category 7: Cross-Tool Workflows (ALL tools must be called)")
    print("=" * 80)

    cross_tool_queries = [
        ("Run full quality check: ruff, pytest, and typecheck", ["ruff_check", "pytest_run", "typecheck"]),
        ("Get git diff and read modified files", ["git_diff", "read_file"]),
        ("Find UserService definition and show hover info", ["goto_definition", "hover"]),
        ("Check git status and diff the staged files", ["git_status", "git_diff"]),
        ("Run tests and lint the failures", ["pytest_run", "ruff_check"]),
    ]

    for query, tools in cross_tool_queries:
        success, response, elapsed = test_query(
            model,
            tokenizer,
            query,
            "Cross-Tool",
            model_path,
            expect_tools=tools,
            expect_all_tools=True,  # **KEY FIX: Require ALL tools**
        )
        results["cross_tool"].append(success)
        times.append(elapsed)

    # Category 8: Discrimination (5 queries)
    print("\n" + "=" * 80)
    print("Category 8: Discrimination (tool vs direct answer)")
    print("=" * 80)

    discrimination_queries = [
        ("What's the difference between hover and goto definition?", True, None),  # Direct
        ("Find all pytest test files", False, ["grep", "workspace_symbols"]),  # Tool
        ("When should I use git status vs git diff?", True, None),  # Direct
        ("Show document symbols for monty_runner.py", False, ["document_symbols"]),  # Tool
        ("What does LSP stand for?", True, None),  # Direct
    ]

    for query, is_direct, tools in discrimination_queries:
        if is_direct:
            success, response, elapsed = test_query(
                model, tokenizer, query, "Discrimination", model_path, expect_no_tools=True
            )
        else:
            success, response, elapsed = test_query(
                model, tokenizer, query, "Discrimination", model_path, expect_tools=tools
            )
        results["discrimination"].append(success)
        times.append(elapsed)

    # Print summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY (HONEST METRICS)")
    print("=" * 80)

    for category, successes in results.items():
        passed = sum(successes)
        total = len(successes)
        percentage = (passed / total * 100) if total > 0 else 0

        # Determine target based on category
        if category in ["direct_answers", "discrimination", "existing_lsp", "existing_tools"]:
            target = 90
        elif category in ["field_access", "new_lsp", "git_tools"]:
            target = 80
        elif category == "cross_tool":
            target = 60
        else:
            target = 80

        status = "✅" if percentage >= target else "❌"
        print(f"{status} {category:20s}: {passed}/{total} ({percentage:.0f}%) [target: {target}%]")

    total_passed = sum(sum(s) for s in results.values())
    total_queries = sum(len(s) for s in results.values())
    overall_percentage = (total_passed / total_queries * 100) if total_queries > 0 else 0

    print(f"\n{'=' * 80}")
    print(f"Overall: {total_passed}/{total_queries} ({overall_percentage:.0f}%)")
    print("Target: ≥85% (34/40)")
    print(f"Status: {'✅ PASS' if overall_percentage >= 85 else '❌ FAIL'}")
    print(f"{'=' * 80}")

    # Performance stats
    avg_time = sum(times) / len(times) if times else 0
    print("\nPerformance:")
    print(f"  Average generation time: {avg_time:.2f}s")
    print(f"  Total validation time: {sum(times):.2f}s")

    return overall_percentage >= 85


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_phase27_validation_fixed.py <model_path>")
        sys.exit(1)

    model_path = sys.argv[1]
    success = run_validation(model_path)
    sys.exit(0 if success else 1)
