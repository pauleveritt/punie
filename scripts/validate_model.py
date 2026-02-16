#!/usr/bin/env python3
"""Comprehensive model validation suite with 6-layer validation and dual scoring.

This script validates model responses across 57 queries (45 single-turn + 12 multi-turn)
in 7 categories using both soft (substring matching) and strict (AST-based) validation layers.

Usage:
    uv run python scripts/validate_model.py <model_path> [options]

    Options:
      --category NAME   Run only one category
      --verbose         Show full response text
      --json            Output results as JSON
      --output FILE     Save detailed results to file
      --max-tokens N    Max tokens for generation (default: 512)

Example:
    uv run python scripts/validate_model.py fused_model_qwen3_phase27_5bit/
    uv run python scripts/validate_model.py fused_model_qwen3_phase27_5bit/ --category field_access
    uv run python scripts/validate_model.py fused_model_qwen3_phase27_5bit/ --category multi_turn
    uv run python scripts/validate_model.py fused_model_qwen3_phase27_5bit/ --verbose --output results.json
"""

import argparse
import ast
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlx.core as mx
from mlx_lm import generate, load
from pydantic import BaseModel

from punie.agent import typed_tools
from punie.agent.prompt_utils import (
    extract_python_from_code_mode,
    extract_tool_calls_from_response,
    format_prompt,
    format_prompt_with_history,
    is_tool_response,
    validate_python_code,
)


# ============================================================================
# Schema Registry (auto-derived from Pydantic models)
# ============================================================================


@dataclass
class ToolSchema:
    """Schema information for a typed tool."""

    tool_name: str
    result_model: type[BaseModel]
    result_fields: set[str]  # Top-level fields
    nested_models: dict[str, type[BaseModel]]  # list_field_name -> nested model
    nested_fields: set[str]  # Fields on nested objects
    all_valid_fields: set[str]  # Union of both


def _extract_fields(model: type[BaseModel]) -> set[str]:
    """Extract field names from a Pydantic model."""
    return set(model.model_fields.keys())


def _build_schema_registry() -> dict[str, ToolSchema]:
    """Build schema registry from typed_tools.py Pydantic models.

    Returns:
        Dict mapping tool_name -> ToolSchema
    """
    registry = {}

    # Define schemas for all 11 typed tools
    schemas = [
        # Quality tools
        (
            "typecheck",
            typed_tools.TypeCheckResult,
            {"errors": typed_tools.TypeCheckError},
        ),
        (
            "ruff_check",
            typed_tools.RuffResult,
            {"violations": typed_tools.RuffViolation},
        ),
        ("pytest_run", typed_tools.TestResult, {"tests": typed_tools.TestCase}),
        # LSP Navigation (existing)
        (
            "goto_definition",
            typed_tools.GotoDefinitionResult,
            {"locations": typed_tools.DefinitionLocation},
        ),
        (
            "find_references",
            typed_tools.FindReferencesResult,
            {"references": typed_tools.ReferenceLocation},
        ),
        # LSP Navigation (Phase 27 new)
        ("hover", typed_tools.HoverResult, {}),
        (
            "document_symbols",
            typed_tools.DocumentSymbolsResult,
            {"symbols": typed_tools.SymbolInfo},
        ),
        (
            "workspace_symbols",
            typed_tools.WorkspaceSymbolsResult,
            {"symbols": typed_tools.WorkspaceSymbol},
        ),
        # Git tools (Phase 27 new)
        (
            "git_status",
            typed_tools.GitStatusResult,
            {"files": typed_tools.GitFileStatus},
        ),
        ("git_diff", typed_tools.GitDiffResult, {"files": typed_tools.DiffFile}),
        ("git_log", typed_tools.GitLogResult, {"commits": typed_tools.GitCommit}),
    ]

    for tool_name, result_model, nested in schemas:
        result_fields = _extract_fields(result_model)
        nested_fields = set()
        for nested_model in nested.values():
            nested_fields.update(_extract_fields(nested_model))

        registry[tool_name] = ToolSchema(
            tool_name=tool_name,
            result_model=result_model,
            result_fields=result_fields,
            nested_models=nested,
            nested_fields=nested_fields,
            all_valid_fields=result_fields | nested_fields,
        )

    return registry


SCHEMA_REGISTRY = _build_schema_registry()


# ============================================================================
# Validation Layers
# ============================================================================


def extract_function_calls(code: str) -> set[str]:
    """Extract function call names from Python code using AST.

    Args:
        code: Python code string

    Returns:
        Set of function names called in the code

    Note:
        This is AST-based, so won't match names in comments or strings.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()

    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.add(node.func.id)

    return calls


def find_result_variable(code: str, tool_name: str) -> str | None:
    """Find the variable name that stores the tool result.

    Args:
        code: Python code string
        tool_name: Tool function name to look for

    Returns:
        Variable name (e.g., "result", "status_result", "r"), or None if not found

    Example:
        >>> find_result_variable("result = typecheck('src/')", "typecheck")
        'result'
        >>> find_result_variable("r = typecheck('src/')", "typecheck")
        'r'
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == tool_name
            and isinstance(node.targets[0], ast.Name)
        ):
            return node.targets[0].id

    return None


def extract_field_accesses(code: str, var_name: str) -> set[str]:
    """Extract field accesses on a specific variable using AST.

    Args:
        code: Python code string
        var_name: Variable name to track (e.g., "result")

    Returns:
        Set of field names accessed on that variable

    Example:
        >>> code = "if result.error_count > 0: print(result.errors)"
        >>> extract_field_accesses(code, "result")
        {'error_count', 'errors'}
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()

    fields = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == var_name
        ):
            fields.add(node.attr)

    return fields


def extract_all_field_accesses(code: str) -> set[str]:
    """Extract ALL attribute access names from Python code, regardless of object.

    This catches field accesses through iteration variables, indexed chains,
    and list comprehension variables. For example:
      - ``for f in result.files: f.staged`` -> includes 'staged'
      - ``result.locations[0].file`` -> includes 'file'
      - ``[s for s in result.symbols if s.kind == 5]`` -> includes 'kind'

    Args:
        code: Python code string

    Returns:
        Set of all attribute names accessed anywhere in the code
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()

    fields = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            fields.add(node.attr)

    return fields


def extract_nested_field_accesses(
    code: str, iter_vars: dict[str, str]
) -> dict[str, set[str]]:
    """Extract field accesses on iteration variables.

    Args:
        code: Python code string
        iter_vars: Dict mapping iteration var -> source field (e.g., {"error": "errors"})

    Returns:
        Dict mapping iteration var -> set of accessed fields

    Example:
        >>> code = "for error in result.errors: print(error.file, error.line)"
        >>> extract_nested_field_accesses(code, {"error": "errors"})
        {'error': {'file', 'line'}}
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}

    accesses: dict[str, set[str]] = {var: set() for var in iter_vars}

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name in iter_vars:
                accesses[var_name].add(node.attr)

    return accesses


@dataclass
class ValidationResult:
    """Result of a single validation layer."""

    layer_name: str
    passed: bool
    detail: str | None = None


def validate_layer1_basic_gate(
    response: str, expected_tool_response: bool
) -> ValidationResult:
    """Layer 1: Check if response is tool call or direct answer.

    Args:
        response: Model response text
        expected_tool_response: True if tool call expected, False if direct answer expected

    Returns:
        ValidationResult with pass/fail
    """
    is_tool = is_tool_response(response)

    if expected_tool_response:
        if is_tool:
            return ValidationResult("gate", True, "Tool call detected")
        else:
            return ValidationResult("gate", False, "Expected tool call, got direct answer")
    else:
        if not is_tool:
            return ValidationResult("gate", True, "Direct answer detected")
        else:
            return ValidationResult("gate", False, "Expected direct answer, got tool call")


def validate_layer2_code_extraction(response: str) -> tuple[ValidationResult, list[str]]:
    """Layer 2: Extract and clean Python code from response.

    Args:
        response: Model response text

    Returns:
        Tuple of (ValidationResult, list of Python code strings)
    """
    # Extract raw tool call blocks
    raw_blocks = extract_tool_calls_from_response(response)
    if not raw_blocks:
        return ValidationResult("extract", False, "No tool call blocks found"), []

    # Strip XML wrappers to get pure Python
    python_blocks = []
    for raw in raw_blocks:
        py = extract_python_from_code_mode(raw)
        if py:
            python_blocks.append(py)

    if not python_blocks:
        return ValidationResult("extract", False, "No Python code extracted"), []

    return ValidationResult("extract", True, f"Extracted {len(python_blocks)} code block(s)"), python_blocks


def validate_layer3_ast(code_blocks: list[str]) -> tuple[ValidationResult, list[str]]:
    """Layer 3: Validate Python code syntax using AST.

    Args:
        code_blocks: List of Python code strings

    Returns:
        Tuple of (ValidationResult, list of valid code strings)
    """
    valid_blocks = []
    errors = []

    for code in code_blocks:
        is_valid, error_msg = validate_python_code(code)
        if is_valid:
            valid_blocks.append(code)
        else:
            errors.append(error_msg)

    if not valid_blocks:
        detail = f"All {len(code_blocks)} code blocks have syntax errors: {errors[0] if errors else 'unknown'}"
        return ValidationResult("ast", False, detail), []

    if errors:
        detail = f"{len(valid_blocks)}/{len(code_blocks)} blocks valid"
        return ValidationResult("ast", True, detail), valid_blocks

    return ValidationResult("ast", True, f"All {len(code_blocks)} blocks valid"), valid_blocks


def validate_layer4_tool_identity(
    code_blocks: list[str], expected_tools: list[str]
) -> ValidationResult:
    """Layer 4: Check if correct tools were called.

    Args:
        code_blocks: List of valid Python code strings
        expected_tools: List of expected tool names (e.g., ["typecheck", "ruff_check"])

    Returns:
        ValidationResult with pass/fail
    """
    # Extract all function calls from code
    all_calls = set()
    for code in code_blocks:
        all_calls.update(extract_function_calls(code))

    # Check if all expected tools are present
    missing = []
    for tool in expected_tools:
        if tool not in all_calls:
            missing.append(tool)

    # Check for run_command fallback (model calling run_command instead of typed tool)
    fallback_detected = False
    if "run_command" in all_calls and any(
        tool in SCHEMA_REGISTRY for tool in expected_tools
    ):
        fallback_detected = True

    if missing:
        detail = f"Missing tools: {', '.join(missing)}"
        return ValidationResult("identity", False, detail)

    if fallback_detected:
        detail = "Model used run_command fallback instead of typed tool"
        return ValidationResult("identity", False, detail)

    detail = f"All {len(expected_tools)} expected tools called"
    return ValidationResult("identity", True, detail)


def validate_layer5_schema(
    code_blocks: list[str], expected_fields: list[str], tool_names: list[str]
) -> ValidationResult:
    """Layer 5: Validate field accesses against Pydantic schemas.

    Args:
        code_blocks: List of valid Python code strings
        expected_fields: List of expected field names to access
        tool_names: List of tool names (for looking up schemas)

    Returns:
        ValidationResult with pass/fail
    """
    if not expected_fields:
        return ValidationResult("schema", True, "No field access expected")

    # Find result variables for each tool
    result_vars: dict[str, str] = {}  # var_name -> tool_name
    for code in code_blocks:
        for tool in tool_names:
            var = find_result_variable(code, tool)
            if var:
                result_vars[var] = tool

    if not result_vars:
        return ValidationResult("schema", False, "Could not find result variable assignment")

    # Extract field accesses for each result variable
    all_accessed_fields = set()
    invalid_fields = []

    for code in code_blocks:
        for var_name, tool_name in result_vars.items():
            # Get schema for this tool
            if tool_name not in SCHEMA_REGISTRY:
                continue

            schema = SCHEMA_REGISTRY[tool_name]

            # Extract direct field accesses (e.g., result.error_count)
            accessed = extract_field_accesses(code, var_name)
            all_accessed_fields.update(accessed)

            # Validate each accessed field
            for field in accessed:
                if field not in schema.all_valid_fields:
                    invalid_fields.append(
                        f"{tool_name}.{field} (valid: {', '.join(sorted(schema.result_fields))})"
                    )

            # Also collect ALL attribute accesses (handles iteration variables,
            # indexed chains like result.locations[0].file, and list comprehension
            # variables like [s for s in result.symbols if s.kind == 5])
            all_accessed_fields.update(extract_all_field_accesses(code))

    if invalid_fields:
        detail = f"Invalid fields: {'; '.join(invalid_fields)}"
        return ValidationResult("schema", False, detail)

    # Check if expected fields were accessed (broadened to catch access through
    # iteration vars, indexing, and comprehensions)
    missing_fields = [f for f in expected_fields if f not in all_accessed_fields]
    if missing_fields:
        detail = f"Expected fields not accessed: {', '.join(missing_fields)}"
        return ValidationResult("schema", False, detail)

    detail = f"All {len(expected_fields)} expected fields accessed correctly"
    return ValidationResult("schema", True, detail)


def validate_layer6_completeness(
    code_blocks: list[str], expected_tools: list[str]
) -> ValidationResult:
    """Layer 6: Check if ALL expected tools were called (cross-tool workflows).

    Args:
        code_blocks: List of valid Python code strings
        expected_tools: List of all expected tool names

    Returns:
        ValidationResult with pass/fail
    """
    # Extract all function calls
    all_calls = set()
    for code in code_blocks:
        all_calls.update(extract_function_calls(code))

    # Check which expected tools are missing
    missing = [tool for tool in expected_tools if tool not in all_calls]

    if missing:
        detail = f"Missing tools: {', '.join(missing)}"
        return ValidationResult("completeness", False, detail)

    detail = f"All {len(expected_tools)} expected tools called"
    return ValidationResult("completeness", True, detail)


def validate_turn2_summary(
    response: str, expected_keywords: list[str]
) -> tuple[ValidationResult, ValidationResult]:
    """Validate turn 2 when a summary is expected (not a tool call).

    Args:
        response: Turn 2 response text
        expected_keywords: Keywords that should appear in the summary

    Returns:
        Tuple of (gate_result, keywords_result)
    """
    # T2-Gate: Response should NOT be a tool call
    is_tool = is_tool_response(response)
    if is_tool:
        gate = ValidationResult("t2-gate", False, "Expected summary, got tool call")
        keywords = ValidationResult("t2-keywords", False, "Skipped (gate failed)")
        return gate, keywords

    gate = ValidationResult("t2-gate", True, "Summary detected (not tool call)")

    # T2-Keywords: Check if ≥50% of expected keywords are present
    response_lower = response.lower()
    matched = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    threshold = len(expected_keywords) * 0.5

    if matched >= threshold:
        keywords = ValidationResult(
            "t2-keywords",
            True,
            f"Matched {matched}/{len(expected_keywords)} keywords",
        )
    else:
        missing = [kw for kw in expected_keywords if kw.lower() not in response_lower]
        keywords = ValidationResult(
            "t2-keywords",
            False,
            f"Only {matched}/{len(expected_keywords)} keywords (missing: {', '.join(missing[:3])}...)",
        )

    return gate, keywords


def validate_turn2_tool_call(
    response: str, expected_tools: list[str]
) -> list[ValidationResult]:
    """Validate turn 2 when a tool call is expected (cross-tool chaining).

    Args:
        response: Turn 2 response text
        expected_tools: List of expected tool names in turn 2

    Returns:
        List of ValidationResults for [t2-gate, t2-extract, t2-ast, t2-identity]
    """
    results = []

    # T2-Gate: Response should be a tool call
    is_tool = is_tool_response(response)
    if not is_tool:
        results.append(
            ValidationResult("t2-gate", False, "Expected tool call, got direct answer")
        )
        # Short-circuit: add placeholder failures
        results.append(ValidationResult("t2-extract", False, "Skipped (gate failed)"))
        results.append(ValidationResult("t2-ast", False, "Skipped (gate failed)"))
        results.append(ValidationResult("t2-identity", False, "Skipped (gate failed)"))
        return results

    results.append(ValidationResult("t2-gate", True, "Tool call detected"))

    # T2-Extract: Extract Python code
    raw_blocks = extract_tool_calls_from_response(response)
    if not raw_blocks:
        results.append(
            ValidationResult("t2-extract", False, "No tool call blocks found")
        )
        results.append(ValidationResult("t2-ast", False, "Skipped (extract failed)"))
        results.append(
            ValidationResult("t2-identity", False, "Skipped (extract failed)")
        )
        return results

    python_blocks = []
    for raw in raw_blocks:
        py = extract_python_from_code_mode(raw)
        if py:
            python_blocks.append(py)

    if not python_blocks:
        results.append(ValidationResult("t2-extract", False, "No Python code extracted"))
        results.append(ValidationResult("t2-ast", False, "Skipped (extract failed)"))
        results.append(
            ValidationResult("t2-identity", False, "Skipped (extract failed)")
        )
        return results

    results.append(
        ValidationResult("t2-extract", True, f"Extracted {len(python_blocks)} code block(s)")
    )

    # T2-AST: Validate syntax
    valid_blocks = []
    errors = []
    for code in python_blocks:
        is_valid, error_msg = validate_python_code(code)
        if is_valid:
            valid_blocks.append(code)
        else:
            errors.append(error_msg)

    if not valid_blocks:
        results.append(
            ValidationResult(
                "t2-ast",
                False,
                f"All {len(python_blocks)} code blocks have syntax errors",
            )
        )
        results.append(ValidationResult("t2-identity", False, "Skipped (ast failed)"))
        return results

    results.append(
        ValidationResult("t2-ast", True, f"{len(valid_blocks)}/{len(python_blocks)} blocks valid")
    )

    # T2-Identity: Check if correct tools were called
    all_calls = set()
    for code in valid_blocks:
        all_calls.update(extract_function_calls(code))

    missing = [tool for tool in expected_tools if tool not in all_calls]

    if missing:
        results.append(
            ValidationResult("t2-identity", False, f"Missing tools: {', '.join(missing)}")
        )
    else:
        results.append(
            ValidationResult(
                "t2-identity", True, f"All {len(expected_tools)} expected tools called"
            )
        )

    return results


# ============================================================================
# Query Definitions
# ============================================================================


@dataclass
class QuerySpec:
    """Specification for a validation query."""

    query: str
    category: str
    expected_is_tool: bool  # True = tool call, False = direct answer
    expected_tools: list[str]  # Empty for direct answers
    expected_fields: list[str]  # Fields that should be accessed
    target_accuracy: float  # 0.0 to 1.0


@dataclass
class FakeToolResponse:
    """Fake tool response injected between turns for reproducible testing."""

    tool_name: str
    response_text: str  # Full <tool_response>...</tool_response> content
    key_facts: list[str]  # Facts the summary should reference


@dataclass
class MultiTurnQuerySpec:
    """Specification for a multi-turn validation query."""

    query: str  # Initial user query
    category: str  # Always "multi_turn"
    turn1_expected_tools: list[str]  # Expected tool calls in turn 1
    turn1_expected_fields: list[str]  # Expected field accesses in turn 1
    fake_response: str  # Key for FAKE_TOOL_RESPONSES dict
    turn2_is_tool_call: bool  # True = expect second tool, False = expect summary
    turn2_expected_tools: list[str]  # If turn 2 is tool call, which tools?
    turn2_expected_keywords: list[str]  # Keywords turn 2 should contain (for summaries)
    target_accuracy: float


# Define all 45 queries
QUERIES = [
    # Cat 1: Direct Answers (5) - Should NOT call tools
    QuerySpec(
        "What is dependency injection and why is it useful in Python?",
        "direct_answers",
        False,
        [],
        [],
        1.0,
    ),
    QuerySpec(
        "What's the difference between git merge and git rebase?",
        "direct_answers",
        False,
        [],
        [],
        1.0,
    ),
    QuerySpec(
        "When should I use Protocol instead of ABC?",
        "direct_answers",
        False,
        [],
        [],
        1.0,
    ),
    QuerySpec(
        "What are the advantages of structured typed tools over raw text output?",
        "direct_answers",
        False,
        [],
        [],
        1.0,
    ),
    QuerySpec(
        "When should I use workspace_symbols vs document_symbols?",
        "direct_answers",
        False,
        [],
        [],
        1.0,
    ),
    # Cat 2: Single-Tool Discrimination (10) - Should call exactly the RIGHT tool
    QuerySpec(
        "Check types in src/punie/agent/",
        "single_tool",
        True,
        ["typecheck"],
        [],
        0.9,
    ),
    QuerySpec("Run ruff linter on src/", "single_tool", True, ["ruff_check"], [], 0.9),
    QuerySpec(
        "Run the test suite in tests/", "single_tool", True, ["pytest_run"], [], 0.9
    ),
    QuerySpec(
        "Where is TypeCheckResult defined?",
        "single_tool",
        True,
        ["goto_definition"],
        [],
        0.9,
    ),
    QuerySpec(
        "Find all references to parse_ty_output",
        "single_tool",
        True,
        ["find_references"],
        [],
        0.9,
    ),
    QuerySpec(
        "Show hover info for BaseModel at src/punie/agent/typed_tools.py line 14",
        "single_tool",
        True,
        ["hover"],
        [],
        0.9,
    ),
    QuerySpec(
        "List all symbols in src/punie/agent/typed_tools.py",
        "single_tool",
        True,
        ["document_symbols"],
        [],
        0.9,
    ),
    QuerySpec(
        "Search the workspace for classes named GitStatusResult",
        "single_tool",
        True,
        ["workspace_symbols"],
        [],
        0.9,
    ),
    QuerySpec(
        "Show the current git status", "single_tool", True, ["git_status"], [], 0.9
    ),
    QuerySpec(
        "Show the last 5 commits", "single_tool", True, ["git_log"], [], 0.9
    ),
    # Cat 3: Tool Identity (5) - Must use typed tool, NOT run_command
    QuerySpec(
        "Check the codebase for type errors",
        "tool_identity",
        True,
        ["typecheck"],
        [],
        0.8,
    ),
    QuerySpec(
        "Lint the source directory", "tool_identity", True, ["ruff_check"], [], 0.8
    ),
    QuerySpec(
        "Execute the test suite and show results",
        "tool_identity",
        True,
        ["pytest_run"],
        [],
        0.8,
    ),
    QuerySpec(
        "Check git working tree for uncommitted changes",
        "tool_identity",
        True,
        ["git_status"],
        [],
        0.8,
    ),
    QuerySpec(
        "Show the diff for staged changes",
        "tool_identity",
        True,
        ["git_diff"],
        [],
        0.8,
    ),
    # Cat 4: Field Access (10) - Must call tool AND access correct fields
    QuerySpec(
        "How many type errors are in src/?",
        "field_access",
        True,
        ["typecheck"],
        ["error_count"],
        0.8,
    ),
    QuerySpec(
        "Show all fixable ruff violations",
        "field_access",
        True,
        ["ruff_check"],
        ["violations", "fixable"],
        0.8,
    ),
    QuerySpec(
        "What's the test pass rate?",
        "field_access",
        True,
        ["pytest_run"],
        ["passed", "failed"],
        0.8,
    ),
    QuerySpec(
        "Show the file path of the definition of UserService",
        "field_access",
        True,
        ["goto_definition"],
        ["locations", "file"],
        0.8,
    ),
    QuerySpec(
        "How many references to parse_ty_output exist?",
        "field_access",
        True,
        ["find_references"],
        ["reference_count"],
        0.8,
    ),
    QuerySpec(
        "Get the type information for BaseModel",
        "field_access",
        True,
        ["hover"],
        ["content"],
        0.8,
    ),
    QuerySpec(
        "Count all symbols in src/punie/agent/config.py",
        "field_access",
        True,
        ["document_symbols"],
        ["symbol_count"],
        0.8,
    ),
    QuerySpec(
        "Find all classes matching 'Result' in the workspace",
        "field_access",
        True,
        ["workspace_symbols"],
        ["symbols", "kind"],
        0.8,
    ),
    QuerySpec(
        "Count staged vs unstaged files in git status",
        "field_access",
        True,
        ["git_status"],
        ["files", "staged"],
        0.8,
    ),
    QuerySpec(
        "Show additions and deletions in the git diff",
        "field_access",
        True,
        ["git_diff"],
        ["additions", "deletions"],
        0.8,
    ),
    # Cat 5: Cross-Tool Workflows (10) - Must call ALL expected tools
    QuerySpec(
        "Run full quality check: ruff, typecheck, and pytest",
        "cross_tool",
        True,
        ["ruff_check", "typecheck", "pytest_run"],
        [],
        0.6,
    ),
    QuerySpec(
        "Find the definition of UserService and then read that file",
        "cross_tool",
        True,
        ["goto_definition", "read_file"],
        [],
        0.6,
    ),
    QuerySpec(
        "Check git status and diff the staged files",
        "cross_tool",
        True,
        ["git_status", "git_diff"],
        [],
        0.6,
    ),
    QuerySpec(
        "Find all references to TypeCheckResult and show hover info for each",
        "cross_tool",
        True,
        ["find_references", "hover"],
        [],
        0.6,
    ),
    QuerySpec(
        "Run tests and if any fail, show the ruff violations in those files",
        "cross_tool",
        True,
        ["pytest_run", "ruff_check"],
        [],
        0.6,
    ),
    QuerySpec(
        "Check types and show errors only in files with ruff violations too",
        "cross_tool",
        True,
        ["typecheck", "ruff_check"],
        [],
        0.6,
    ),
    QuerySpec(
        "Get document symbols for config.py and hover on the first class",
        "cross_tool",
        True,
        ["document_symbols", "hover"],
        [],
        0.6,
    ),
    QuerySpec(
        "Check git status and read the content of modified files",
        "cross_tool",
        True,
        ["git_status", "read_file"],
        [],
        0.6,
    ),
    QuerySpec(
        "Run ruff check and write a summary report to report.txt",
        "cross_tool",
        True,
        ["ruff_check", "write_file"],
        [],
        0.6,
    ),
    QuerySpec(
        "Search workspace for 'Result' classes and list symbols for each file",
        "cross_tool",
        True,
        ["workspace_symbols", "document_symbols"],
        [],
        0.6,
    ),
    # Cat 6: Discrimination Edge Cases (5) - Ambiguous queries testing judgment
    QuerySpec(
        "What does the typecheck function return?",
        "edge_cases",
        False,
        [],
        [],
        0.8,
    ),
    QuerySpec(
        "How does git_diff handle staged changes?",
        "edge_cases",
        False,
        [],
        [],
        0.8,
    ),
    QuerySpec(
        "Find all Python files in src/",
        "edge_cases",
        True,
        ["run_command"],
        [],
        0.8,
    ),  # Could also use workspace_symbols
    QuerySpec(
        "What's in the test results?",
        "edge_cases",
        True,
        ["pytest_run"],
        [],
        0.8,
    ),
    QuerySpec(
        "Explain what TypeCheckError fields mean",
        "edge_cases",
        False,
        [],
        [],
        0.8,
    ),
]


# 7 Fake Tool Responses (static, reproducible)
FAKE_TOOL_RESPONSES = {
    "typecheck_errors": FakeToolResponse(
        tool_name="typecheck",
        response_text="""<tool_response>
TypeCheckResult(error_count=3, errors=[TypeCheckError(file='src/agent/config.py', line=42, column=8, message='Incompatible types in assignment', severity='error', code='assignment'), TypeCheckError(file='src/agent/factory.py', line=89, column=15, message='Argument 1 has incompatible type', severity='error', code='arg-type'), TypeCheckError(file='tests/test_config.py', line=23, column=12, message='Name "undefined_var" is not defined', severity='error', code='name-defined')])
</tool_response>""",
        key_facts=["3", "error", "assignment", "arg-type"],
    ),
    "ruff_violations": FakeToolResponse(
        tool_name="ruff_check",
        response_text="""<tool_response>
RuffResult(violation_count=2, violations=[RuffViolation(file='src/agent/config.py', line=15, column=1, code='F401', message='module imported but unused', severity='warning', fixable=True), RuffViolation(file='src/agent/factory.py', line=67, column=80, code='E501', message='line too long (95 > 88)', severity='warning', fixable=False)])
</tool_response>""",
        key_facts=["2", "violation", "fixable", "F401"],
    ),
    "pytest_failures": FakeToolResponse(
        tool_name="pytest_run",
        response_text="""<tool_response>
TestResult(total=10, passed=8, failed=2, skipped=0, duration=2.34, tests=[TestCase(name='test_typecheck', file='tests/test_typed_tools.py', outcome='passed', duration=0.12), TestCase(name='test_ruff_check', file='tests/test_typed_tools.py', outcome='passed', duration=0.08), TestCase(name='test_config_validation', file='tests/test_config.py', outcome='failed', duration=0.45), TestCase(name='test_factory_creation', file='tests/test_factory.py', outcome='failed', duration=0.32)])
</tool_response>""",
        key_facts=["8", "passed", "2", "failed"],
    ),
    "git_status_dirty": FakeToolResponse(
        tool_name="git_status",
        response_text="""<tool_response>
GitStatusResult(branch='feature/multi-turn', ahead=2, behind=0, files=[GitFileStatus(path='src/agent/config.py', status='modified', staged=True), GitFileStatus(path='src/agent/factory.py', status='modified', staged=False), GitFileStatus(path='docs/notes.md', status='untracked', staged=False)])
</tool_response>""",
        key_facts=["3", "modified", "staged", "untracked"],
    ),
    "git_diff_changes": FakeToolResponse(
        tool_name="git_diff",
        response_text="""<tool_response>
GitDiffResult(file_count=2, additions=15, deletions=8, files=[DiffFile(path='src/agent/config.py', additions=10, deletions=3, hunks=2), DiffFile(path='src/agent/factory.py', additions=5, deletions=5, hunks=1)])
</tool_response>""",
        key_facts=["15", "addition", "8", "deletion"],
    ),
    "goto_def_found": FakeToolResponse(
        tool_name="goto_definition",
        response_text="""<tool_response>
GotoDefinitionResult(found=True, locations=[DefinitionLocation(file='src/services/user.py', line=15, column=6, symbol='UserService', kind='class')])
</tool_response>""",
        key_facts=["src/services/user.py", "15", "UserService"],
    ),
    "find_refs_multiple": FakeToolResponse(
        tool_name="find_references",
        response_text="""<tool_response>
FindReferencesResult(reference_count=5, references=[ReferenceLocation(file='src/agent/typed_tools.py', line=42, column=12), ReferenceLocation(file='src/agent/typed_tools.py', line=58, column=8), ReferenceLocation(file='tests/test_typed_tools.py', line=89, column=15), ReferenceLocation(file='tests/test_typed_tools.py', line=134, column=20), ReferenceLocation(file='scripts/validate_model.py', line=267, column=25)])
</tool_response>""",
        key_facts=["5", "reference", "parse_ty_output"],
    ),
}


# 12 Multi-Turn Queries (8 summary + 4 cross-tool chaining)
MULTI_TURN_QUERIES = [
    # Group A: Summary After Tool Response (8 queries, target: 70%)
    MultiTurnQuerySpec(
        query="How many type errors are in src/?",
        category="multi_turn",
        turn1_expected_tools=["typecheck"],
        turn1_expected_fields=[],
        fake_response="typecheck_errors",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["3", "error"],
        target_accuracy=0.7,
    ),
    MultiTurnQuerySpec(
        query="Check if the tests pass",
        category="multi_turn",
        turn1_expected_tools=["pytest_run"],
        turn1_expected_fields=[],
        fake_response="pytest_failures",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["2", "fail"],
        target_accuracy=0.7,
    ),
    MultiTurnQuerySpec(
        query="Run ruff linter on the codebase",
        category="multi_turn",
        turn1_expected_tools=["ruff_check"],
        turn1_expected_fields=[],
        fake_response="ruff_violations",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["2", "violation"],
        target_accuracy=0.7,
    ),
    MultiTurnQuerySpec(
        query="Show the current git status",
        category="multi_turn",
        turn1_expected_tools=["git_status"],
        turn1_expected_fields=[],
        fake_response="git_status_dirty",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["3", "modified"],
        target_accuracy=0.7,
    ),
    MultiTurnQuerySpec(
        query="Show the diff for staged changes",
        category="multi_turn",
        turn1_expected_tools=["git_diff"],
        turn1_expected_fields=[],
        fake_response="git_diff_changes",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["addition", "deletion"],
        target_accuracy=0.7,
    ),
    MultiTurnQuerySpec(
        query="Where is UserService defined?",
        category="multi_turn",
        turn1_expected_tools=["goto_definition"],
        turn1_expected_fields=[],
        fake_response="goto_def_found",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["src/services/user.py", "15"],
        target_accuracy=0.7,
    ),
    MultiTurnQuerySpec(
        query="How many references to parse_ty_output exist?",
        category="multi_turn",
        turn1_expected_tools=["find_references"],
        turn1_expected_fields=[],
        fake_response="find_refs_multiple",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["5", "reference"],
        target_accuracy=0.7,
    ),
    MultiTurnQuerySpec(
        query="What's the test pass rate?",
        category="multi_turn",
        turn1_expected_tools=["pytest_run"],
        turn1_expected_fields=[],
        fake_response="pytest_failures",
        turn2_is_tool_call=False,
        turn2_expected_tools=[],
        turn2_expected_keywords=["8", "passed", "2", "failed"],
        target_accuracy=0.7,
    ),
    # Group B: Cross-Tool Chaining (4 queries, target: 60%)
    MultiTurnQuerySpec(
        query="Check types and if errors exist, show ruff violations too",
        category="multi_turn",
        turn1_expected_tools=["typecheck"],
        turn1_expected_fields=[],
        fake_response="typecheck_errors",
        turn2_is_tool_call=True,
        turn2_expected_tools=["ruff_check"],
        turn2_expected_keywords=[],
        target_accuracy=0.6,
    ),
    MultiTurnQuerySpec(
        query="Find where UserService is defined and read that file",
        category="multi_turn",
        turn1_expected_tools=["goto_definition"],
        turn1_expected_fields=[],
        fake_response="goto_def_found",
        turn2_is_tool_call=True,
        turn2_expected_tools=["read_file"],
        turn2_expected_keywords=[],
        target_accuracy=0.6,
    ),
    MultiTurnQuerySpec(
        query="Run tests. If any fail, check types in those files",
        category="multi_turn",
        turn1_expected_tools=["pytest_run"],
        turn1_expected_fields=[],
        fake_response="pytest_failures",
        turn2_is_tool_call=True,
        turn2_expected_tools=["typecheck"],
        turn2_expected_keywords=[],
        target_accuracy=0.6,
    ),
    MultiTurnQuerySpec(
        query="Check git status and diff the staged files",
        category="multi_turn",
        turn1_expected_tools=["git_status"],
        turn1_expected_fields=[],
        fake_response="git_status_dirty",
        turn2_is_tool_call=True,
        turn2_expected_tools=["git_diff"],
        turn2_expected_keywords=[],
        target_accuracy=0.6,
    ),
]


# ============================================================================
# Validation Engine
# ============================================================================


def validate_query(
    query_spec: QuerySpec,
    response: str,
    verbose: bool = False,
) -> tuple[bool, bool, list[ValidationResult]]:
    """Validate a single query response through all 6 layers.

    Args:
        query_spec: Query specification
        response: Model response text
        verbose: If True, print detailed layer results

    Returns:
        Tuple of (soft_passed, strict_passed, layer_results)
    """
    layer_results: list[ValidationResult] = []

    # Layer 1: Basic Gate
    gate = validate_layer1_basic_gate(response, query_spec.expected_is_tool)
    layer_results.append(gate)
    if not gate.passed:
        # Short-circuit on gate failure
        return False, False, layer_results

    # If direct answer expected, we're done (soft and strict both pass)
    if not query_spec.expected_is_tool:
        return True, True, layer_results

    # Layer 2: Code Extraction
    extract, code_blocks = validate_layer2_code_extraction(response)
    layer_results.append(extract)
    if not extract.passed:
        # Soft pass if gate passed (substring matching), strict fail
        return True, False, layer_results

    # Layer 3: AST Validation
    ast_result, valid_blocks = validate_layer3_ast(code_blocks)
    layer_results.append(ast_result)
    if not ast_result.passed:
        return True, False, layer_results

    # Layer 4: Tool Identity
    identity = validate_layer4_tool_identity(valid_blocks, query_spec.expected_tools)
    layer_results.append(identity)
    if not identity.passed:
        return True, False, layer_results

    # Layer 5: Schema Validation (only if fields expected)
    if query_spec.expected_fields:
        schema = validate_layer5_schema(
            valid_blocks, query_spec.expected_fields, query_spec.expected_tools
        )
        layer_results.append(schema)
        if not schema.passed:
            return True, False, layer_results
    else:
        layer_results.append(ValidationResult("schema", True, "No fields expected"))

    # Layer 6: Completeness (for cross-tool workflows)
    if len(query_spec.expected_tools) > 1:
        completeness = validate_layer6_completeness(
            valid_blocks, query_spec.expected_tools
        )
        layer_results.append(completeness)
        if not completeness.passed:
            return True, False, layer_results
    else:
        layer_results.append(ValidationResult("completeness", True, "Single tool"))

    # All layers passed!
    return True, True, layer_results


def run_multi_turn_query(
    query_spec: MultiTurnQuerySpec,
    model: Any,
    tokenizer: Any,
    model_path: Path,
    max_tokens: int,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run a multi-turn query with fake tool response injection.

    Args:
        query_spec: Multi-turn query specification
        model: Loaded model
        tokenizer: Loaded tokenizer
        model_path: Path to model directory
        max_tokens: Max tokens for generation
        verbose: If True, show detailed output

    Returns:
        Dict with turn1/turn2 results and overall pass/fail status
    """
    # ===== TURN 1: Generate initial response =====
    prompt = format_prompt(query_spec.query, model_path)
    start_time = time.time()
    turn1_response = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        verbose=False,
    )
    turn1_time = time.time() - start_time

    # Validate turn 1 (layers 1-4)
    turn1_spec = QuerySpec(
        query=query_spec.query,
        category="multi_turn",
        expected_is_tool=True,
        expected_tools=query_spec.turn1_expected_tools,
        expected_fields=query_spec.turn1_expected_fields,
        target_accuracy=query_spec.target_accuracy,
    )
    turn1_soft, turn1_strict, turn1_layers = validate_query(
        turn1_spec, turn1_response, verbose
    )

    # ===== INJECT FAKE TOOL RESPONSE =====
    fake_response = FAKE_TOOL_RESPONSES[query_spec.fake_response]

    # Build conversation history for turn 2
    # History format: list of {"role": ..., "content": ...} dicts
    history = [
        {"role": "user", "content": query_spec.query},  # Original query
        {"role": "assistant", "content": turn1_response},  # Assistant's turn 1 response (with tool call)
    ]

    # ===== TURN 2: Generate response to tool response =====
    # The tool response becomes the new "query" and previous turns become history
    prompt_turn2 = format_prompt_with_history(
        fake_response.response_text, model_path, history
    )
    start_time = time.time()
    turn2_response = generate(
        model,
        tokenizer,
        prompt=prompt_turn2,
        max_tokens=max_tokens,
        verbose=False,
    )
    turn2_time = time.time() - start_time

    # Validate turn 2
    if query_spec.turn2_is_tool_call:
        # Expect a tool call (cross-tool chaining)
        turn2_layers = validate_turn2_tool_call(
            turn2_response, query_spec.turn2_expected_tools
        )
        turn2_soft = turn2_layers[0].passed  # T2-gate
        turn2_strict = all(layer.passed for layer in turn2_layers)
    else:
        # Expect a summary (not a tool call)
        t2_gate, t2_keywords = validate_turn2_summary(
            turn2_response, query_spec.turn2_expected_keywords
        )
        turn2_layers = [t2_gate, t2_keywords]
        turn2_soft = t2_gate.passed
        turn2_strict = t2_gate.passed and t2_keywords.passed

    # Overall pass: both turns must pass
    overall_soft = turn1_soft and turn2_soft
    overall_strict = turn1_strict and turn2_strict

    return {
        "query": query_spec.query,
        "category": "multi_turn",
        "soft_pass": overall_soft,
        "strict_pass": overall_strict,
        "turn1": {
            "response": turn1_response if verbose else None,
            "soft_pass": turn1_soft,
            "strict_pass": turn1_strict,
            "gen_time": turn1_time,
            "layers": [
                {"name": l.layer_name, "passed": l.passed, "detail": l.detail}
                for l in turn1_layers
            ],
        },
        "turn2": {
            "response": turn2_response if verbose else None,
            "soft_pass": turn2_soft,
            "strict_pass": turn2_strict,
            "gen_time": turn2_time,
            "layers": [
                {"name": l.layer_name, "passed": l.passed, "detail": l.detail}
                for l in turn2_layers
            ],
        },
    }


# ============================================================================
# Main
# ============================================================================


def run_validation(
    model_path: Path,
    category_filter: str | None = None,
    verbose: bool = False,
    max_tokens: int = 512,
) -> list[dict[str, Any]]:
    """Run validation suite against a model.

    Args:
        model_path: Path to model directory
        category_filter: If set, only run this category
        verbose: If True, show full response text
        max_tokens: Max tokens for generation

    Returns:
        List of result dicts with scores and details
    """
    print(f"Loading model: {model_path}")
    model, tokenizer = load(str(model_path))
    mx.random.seed(42)

    # Filter queries by category if requested
    single_turn_queries = QUERIES
    multi_turn_queries = MULTI_TURN_QUERIES

    if category_filter:
        if category_filter == "multi_turn":
            # Only multi-turn queries
            single_turn_queries = []
        else:
            # Only specified single-turn category
            single_turn_queries = [q for q in QUERIES if q.category == category_filter]
            multi_turn_queries = []

        total = len(single_turn_queries) + len(multi_turn_queries)
        if total == 0:
            print(f"No queries found for category: {category_filter}")
            sys.exit(1)
        print(f"Running {total} queries in category: {category_filter}\n")
    else:
        # Run all queries (45 single-turn + 12 multi-turn = 57 total)
        total = len(single_turn_queries) + len(multi_turn_queries)
        print(f"Running all {total} queries ({len(single_turn_queries)} single-turn + {len(multi_turn_queries)} multi-turn)\n")

    # Run all queries
    results = []
    query_num = 0

    # ===== SINGLE-TURN QUERIES =====
    for query_spec in single_turn_queries:
        query_num += 1

        # Generate response
        prompt = format_prompt(query_spec.query, model_path)

        start_time = time.time()
        response_text = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            verbose=False,
        )
        gen_time = time.time() - start_time

        # Validate
        soft_pass, strict_pass, layers = validate_query(
            query_spec, response_text, verbose
        )

        # Format layer status
        layer_status = []
        for layer in layers:
            status = "OK" if layer.passed else "FAIL"
            layer_status.append(f"{layer.layer_name}:{status}")

        # Print result
        soft_label = "PASS" if soft_pass else "FAIL"
        strict_label = "PASS" if strict_pass else "FAIL"
        print(
            f"[{query_num}/{total}] {query_spec.category} | {query_spec.query[:60]}..."
        )
        print(f"  Soft: {soft_label}  Strict: {strict_label}  ({gen_time:.2f}s)")
        print(f"  Layers: [{'] ['.join(layer_status)}]")

        if not strict_pass:
            print("  Issues:")
            for layer in layers:
                if not layer.passed and layer.detail:
                    print(f"    - {layer.detail}")

        if verbose:
            print(f"  Response:\n{response_text}\n")

        print()

        results.append(
            {
                "query": query_spec.query,
                "category": query_spec.category,
                "soft_pass": soft_pass,
                "strict_pass": strict_pass,
                "gen_time": gen_time,
                "layers": [
                    {"name": l.layer_name, "passed": l.passed, "detail": l.detail}
                    for l in layers
                ],
                "response": response_text if verbose else None,
            }
        )

    # ===== MULTI-TURN QUERIES =====
    for query_spec in multi_turn_queries:
        query_num += 1

        # Run multi-turn query
        result = run_multi_turn_query(
            query_spec, model, tokenizer, model_path, max_tokens, verbose
        )

        # Print result
        soft_label = "PASS" if result["soft_pass"] else "FAIL"
        strict_label = "PASS" if result["strict_pass"] else "FAIL"
        print(f"[{query_num}/{total}] {result['category']} | {result['query'][:60]}...")

        # Turn 1
        t1 = result["turn1"]
        t1_soft = "PASS" if t1["soft_pass"] else "FAIL"
        t1_strict = "PASS" if t1["strict_pass"] else "FAIL"
        t1_layer_status = [
            f"{l['name']}:{'OK' if l['passed'] else 'FAIL'}" for l in t1["layers"]
        ]
        print(f"  Turn 1: Soft: {t1_soft}  Strict: {t1_strict}  ({t1['gen_time']:.2f}s)")
        print(f"    Layers: [{'] ['.join(t1_layer_status)}]")

        # Turn 2
        t2 = result["turn2"]
        t2_soft = "PASS" if t2["soft_pass"] else "FAIL"
        t2_strict = "PASS" if t2["strict_pass"] else "FAIL"
        t2_layer_status = [
            f"{l['name']}:{'OK' if l['passed'] else 'FAIL'}" for l in t2["layers"]
        ]
        print(f"  Turn 2: Soft: {t2_soft}  Strict: {t2_strict}  ({t2['gen_time']:.2f}s)")
        print(f"    Layers: [{'] ['.join(t2_layer_status)}]")

        # Show issues
        if not result["strict_pass"]:
            print("  Issues:")
            for layer in t1["layers"]:
                if not layer["passed"] and layer["detail"]:
                    print(f"    - Turn 1: {layer['detail']}")
            for layer in t2["layers"]:
                if not layer["passed"] and layer["detail"]:
                    print(f"    - Turn 2: {layer['detail']}")

        if verbose:
            print(f"  Turn 1 Response:\n{t1['response']}\n")
            print(f"  Turn 2 Response:\n{t2['response']}\n")

        print()

        results.append(result)

    return results


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize validation results by category.

    Args:
        results: List of result dicts from run_validation

    Returns:
        Summary dict with per-category scores and overall stats
    """
    # Group by category
    by_category: dict[str, list[dict]] = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r)

    # Compute scores per category
    category_scores = {}
    for cat, cat_results in by_category.items():
        soft_pass = sum(1 for r in cat_results if r["soft_pass"])
        strict_pass = sum(1 for r in cat_results if r["strict_pass"])
        total = len(cat_results)

        category_scores[cat] = {
            "soft": (soft_pass, total),
            "strict": (strict_pass, total),
            "soft_pct": (soft_pass / total * 100) if total > 0 else 0,
            "strict_pct": (strict_pass / total * 100) if total > 0 else 0,
        }

    # Overall scores
    total = len(results)
    soft_total = sum(1 for r in results if r["soft_pass"])
    strict_total = sum(1 for r in results if r["strict_pass"])

    return {
        "total": total,
        "soft_pass": soft_total,
        "strict_pass": strict_total,
        "soft_pct": (soft_total / total * 100) if total > 0 else 0,
        "strict_pct": (strict_total / total * 100) if total > 0 else 0,
        "categories": category_scores,
    }


def print_summary(summary: dict[str, Any]):
    """Print validation summary.

    Args:
        summary: Summary dict from summarize_results
    """
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80 + "\n")

    # Category results
    print(f"{'Category':<20} {'Soft':<15} {'Strict':<15} {'Target':<10} {'Status'}")
    print("-" * 80)

    # Get target accuracy per category
    category_targets = {}
    for q in QUERIES:
        if q.category not in category_targets:
            category_targets[q.category] = q.target_accuracy

    for cat, scores in sorted(summary["categories"].items()):
        soft_score = f"{scores['soft'][0]}/{scores['soft'][1]} ({scores['soft_pct']:.0f}%)"
        strict_score = f"{scores['strict'][0]}/{scores['strict'][1]} ({scores['strict_pct']:.0f}%)"
        target = f"{category_targets.get(cat, 0.8) * 100:.0f}%"

        # Determine status (based on strict score vs target)
        met_target = scores["strict_pct"] >= (category_targets.get(cat, 0.8) * 100)
        status = "✅ PASS" if met_target else "❌ FAIL"

        print(f"{cat:<20} {soft_score:<15} {strict_score:<15} {target:<10} {status}")

    print("-" * 80)
    overall_soft = f"{summary['soft_pass']}/{summary['total']} ({summary['soft_pct']:.0f}%)"
    overall_strict = f"{summary['strict_pass']}/{summary['total']} ({summary['strict_pct']:.0f}%)"
    print(f"{'OVERALL:':<20} {overall_soft:<15} {overall_strict:<15} {'≥80%':<10}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate model with comprehensive 6-layer suite"
    )
    parser.add_argument("model_path", type=Path, help="Path to model directory")
    parser.add_argument(
        "--category",
        type=str,
        help="Run only one category (direct_answers, single_tool, tool_identity, field_access, cross_tool, edge_cases, multi_turn)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show full response text"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output results as JSON"
    )
    parser.add_argument("--output", type=Path, help="Save detailed results to file")
    parser.add_argument(
        "--max-tokens", type=int, default=512, help="Max tokens for generation"
    )

    args = parser.parse_args()

    if not args.model_path.exists():
        print(f"Error: Model path does not exist: {args.model_path}")
        sys.exit(1)

    # Run validation
    results = run_validation(
        args.model_path,
        category_filter=args.category,
        verbose=args.verbose,
        max_tokens=args.max_tokens,
    )

    # Summarize
    summary = summarize_results(results)

    # Print summary (unless JSON output)
    if not args.json_output:
        print_summary(summary)

    # Save to file if requested
    if args.output:
        output_data = {"summary": summary, "results": results}
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Detailed results saved to: {args.output}")

    # Output JSON if requested
    if args.json_output:
        output_data = {"summary": summary, "results": results}
        print(json.dumps(output_data, indent=2))

    # Exit with code 0 if overall ≥80% strict, else 1
    sys.exit(0 if summary["strict_pct"] >= 80.0 else 1)


if __name__ == "__main__":
    main()
