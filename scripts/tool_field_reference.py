#!/usr/bin/env python3
"""Auto-generate field reference from Pydantic models and cross-check with stubs.

This script extracts field names and types from all Result models in typed_tools.py
and cross-references them with the stubs in stubs.py to detect mismatches.

Usage:
    uv run python scripts/tool_field_reference.py [--format json|markdown]
"""

import argparse
import json
import sys
from typing import Any

from pydantic import BaseModel
from punie.agent import typed_tools


def extract_model_fields(model: type[BaseModel]) -> dict[str, str]:
    """Extract field names and types from a Pydantic model.

    Args:
        model: Pydantic model class

    Returns:
        Dict mapping field name to type string
    """
    fields = {}
    for field_name, field_info in model.model_fields.items():
        # Format the type annotation
        annotation = field_info.annotation
        if hasattr(annotation, "__name__"):
            type_str = annotation.__name__
        else:
            type_str = str(annotation).replace("typing.", "")
        fields[field_name] = type_str
    return fields


def get_all_result_models() -> dict[str, dict[str, str]]:
    """Get all Result models and their fields from typed_tools.py.

    Returns:
        Dict mapping model name to fields dict
    """
    models = {}

    # Quality tools (existing)
    models["TypeCheckResult"] = extract_model_fields(typed_tools.TypeCheckResult)
    models["TypeCheckError"] = extract_model_fields(typed_tools.TypeCheckError)
    models["RuffResult"] = extract_model_fields(typed_tools.RuffResult)
    models["RuffViolation"] = extract_model_fields(typed_tools.RuffViolation)
    models["TestResult"] = extract_model_fields(typed_tools.TestResult)
    models["TestCase"] = extract_model_fields(typed_tools.TestCase)

    # LSP Navigation (existing)
    models["GotoDefinitionResult"] = extract_model_fields(typed_tools.GotoDefinitionResult)
    models["DefinitionLocation"] = extract_model_fields(typed_tools.DefinitionLocation)
    models["FindReferencesResult"] = extract_model_fields(typed_tools.FindReferencesResult)
    models["ReferenceLocation"] = extract_model_fields(typed_tools.ReferenceLocation)

    # LSP Navigation (Phase 27 new)
    models["HoverResult"] = extract_model_fields(typed_tools.HoverResult)
    models["DocumentSymbolsResult"] = extract_model_fields(typed_tools.DocumentSymbolsResult)
    models["SymbolInfo"] = extract_model_fields(typed_tools.SymbolInfo)
    models["WorkspaceSymbolsResult"] = extract_model_fields(typed_tools.WorkspaceSymbolsResult)
    models["WorkspaceSymbol"] = extract_model_fields(typed_tools.WorkspaceSymbol)

    # Git tools (Phase 27 new)
    models["GitStatusResult"] = extract_model_fields(typed_tools.GitStatusResult)
    models["GitFileStatus"] = extract_model_fields(typed_tools.GitFileStatus)
    models["GitDiffResult"] = extract_model_fields(typed_tools.GitDiffResult)
    models["DiffFile"] = extract_model_fields(typed_tools.DiffFile)
    models["GitLogResult"] = extract_model_fields(typed_tools.GitLogResult)
    models["GitCommit"] = extract_model_fields(typed_tools.GitCommit)

    return models


def check_stub_consistency() -> list[dict[str, Any]]:
    """Check if stubs mention fields that don't exist in models.

    Returns:
        List of mismatches found, each a dict with details
    """
    from punie.agent.stubs import generate_stubs

    stubs_text = generate_stubs()
    models = get_all_result_models()

    mismatches = []

    # Common field access patterns to check
    # Examples: "result.errors", "error.file", "loc.line", "ref.column", etc.
    lines = stubs_text.split("\n")

    # Track which result model each function returns
    tool_to_result = {
        "typecheck": "TypeCheckResult",
        "ruff_check": "RuffResult",
        "pytest_run": "TestResult",
        "goto_definition": "GotoDefinitionResult",
        "find_references": "FindReferencesResult",
        "hover": "HoverResult",
        "document_symbols": "DocumentSymbolsResult",
        "workspace_symbols": "WorkspaceSymbolsResult",
        "git_status": "GitStatusResult",
        "git_diff": "GitDiffResult",
        "git_log": "GitLogResult",
    }

    # Nested model access patterns
    nested_models = {
        "TypeCheckResult": {"errors": "TypeCheckError"},
        "RuffResult": {"violations": "RuffViolation"},
        "TestResult": {"tests": "TestCase"},
        "GotoDefinitionResult": {"locations": "DefinitionLocation"},
        "FindReferencesResult": {"references": "ReferenceLocation"},
        "DocumentSymbolsResult": {"symbols": "SymbolInfo"},
        "WorkspaceSymbolsResult": {"symbols": "WorkspaceSymbol"},
        "GitStatusResult": {"files": "GitFileStatus"},
        "GitDiffResult": {"files": "DiffFile"},
        "GitLogResult": {"commits": "GitCommit"},
    }

    # Track which function context we're in by looking for function definitions
    import re
    current_function = None

    # Check stub examples for field access
    for line in lines:
        # Update current function context
        func_match = re.match(r'def (\w+)\(', line)
        if func_match:
            current_function = func_match.group(1)

        # Look for field access patterns like "result.field_name" or "error.field_name"
        pattern = r'(\w+)\.(\w+)'
        for match in re.finditer(pattern, line):
            var_name, field_name = match.groups()

            # Skip common Python methods/attributes
            if field_name in ["strip", "split", "format", "count", "append", "get"]:
                continue

            # Try to determine which model this variable refers to
            # In stub examples:
            # - "result" usually refers to the return type of current function
            # - "error", "violation", "test" refer to items in lists
            # - "loc", "ref" refer to location objects
            # - "symbol", "commit", "file" refer to nested objects

            # Map variable names to likely model types
            var_to_model = {
                "error": "TypeCheckError",
                "violation": "RuffViolation",
                "test": "TestCase",
                "loc": "DefinitionLocation",
                "ref": "ReferenceLocation",
                "symbol": "SymbolInfo",  # Could also be WorkspaceSymbol
                "commit": "GitCommit",
                "file": "DiffFile",  # Could also be GitFileStatus
                "match": "WorkspaceSymbol",  # Used in workspace_symbols examples
                "status": "GitFileStatus",  # Used in git_status examples
            }

            # For "result" variable, determine model from current function
            if var_name == "result" and current_function:
                var_to_model["result"] = tool_to_result.get(current_function)

            model_name = var_to_model.get(var_name)

            # If we can determine the model, check if field exists
            if model_name and model_name in models:
                fields = models[model_name]
                if field_name not in fields:
                    mismatches.append({
                        "location": "stubs.py example",
                        "line": line.strip(),
                        "model": model_name,
                        "field": field_name,
                        "issue": f"Field '{field_name}' not found in {model_name}",
                        "available_fields": list(fields.keys()),
                    })

    return mismatches


def format_as_json(models: dict[str, dict[str, str]], mismatches: list[dict[str, Any]]) -> str:
    """Format reference as JSON.

    Args:
        models: Model fields dict
        mismatches: List of detected mismatches

    Returns:
        JSON string
    """
    output = {
        "models": models,
        "mismatches": mismatches,
    }
    return json.dumps(output, indent=2)


def format_as_markdown(models: dict[str, dict[str, str]], mismatches: list[dict[str, Any]]) -> str:
    """Format reference as Markdown.

    Args:
        models: Model fields dict
        mismatches: List of detected mismatches

    Returns:
        Markdown string
    """
    lines = ["# Tool Field Reference", ""]
    lines.append("Auto-generated from `src/punie/agent/typed_tools.py`")
    lines.append("")

    # Group models by category
    categories = {
        "Quality Tools": [
            "TypeCheckResult", "TypeCheckError",
            "RuffResult", "RuffViolation",
            "TestResult", "TestCase",
        ],
        "LSP Navigation (Existing)": [
            "GotoDefinitionResult", "DefinitionLocation",
            "FindReferencesResult", "ReferenceLocation",
        ],
        "LSP Navigation (Phase 27)": [
            "HoverResult",
            "DocumentSymbolsResult", "SymbolInfo",
            "WorkspaceSymbolsResult", "WorkspaceSymbol",
        ],
        "Git Tools (Phase 27)": [
            "GitStatusResult", "GitFileStatus",
            "GitDiffResult", "DiffFile",
            "GitLogResult", "GitCommit",
        ],
    }

    for category, model_names in categories.items():
        lines.append(f"## {category}")
        lines.append("")

        for model_name in model_names:
            if model_name not in models:
                continue

            fields = models[model_name]
            lines.append(f"### `{model_name}`")
            lines.append("")

            # Table header
            lines.append("| Field | Type |")
            lines.append("|-------|------|")

            for field_name, field_type in fields.items():
                lines.append(f"| `{field_name}` | `{field_type}` |")

            lines.append("")

    # Add mismatches section if any
    if mismatches:
        lines.append("## ⚠️ Mismatches Detected")
        lines.append("")
        lines.append("The following field accesses in stubs don't match the actual models:")
        lines.append("")

        for mismatch in mismatches:
            lines.append(f"**{mismatch['model']}.{mismatch['field']}**")
            lines.append(f"- Issue: {mismatch['issue']}")
            lines.append(f"- Location: {mismatch['location']}")
            lines.append(f"- Line: `{mismatch['line']}`")
            lines.append(f"- Available fields: {', '.join(f'`{f}`' for f in mismatch['available_fields'])}")
            lines.append("")
    else:
        lines.append("## ✅ No Mismatches")
        lines.append("")
        lines.append("All field accesses in stubs match the actual Pydantic models.")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate field reference from Pydantic models"
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    args = parser.parse_args()

    # Extract all models and their fields
    models = get_all_result_models()

    # Check for mismatches with stubs
    mismatches = check_stub_consistency()

    # Format and print
    if args.format == "json":
        print(format_as_json(models, mismatches))
    else:
        print(format_as_markdown(models, mismatches))

    # Exit with error code if mismatches found
    if mismatches:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
