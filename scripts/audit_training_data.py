#!/usr/bin/env python
"""Audit training data for format consistency and quality issues.

Pre-training check that catches format mismatches and data quality issues
BEFORE wasting hours on training.

Usage:
    uv run python scripts/audit_training_data.py data/phase26_balanced/train.jsonl

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import json
import sys
from pathlib import Path
from collections import Counter


def load_examples(path: Path) -> list[dict]:
    """Load JSONL training examples."""
    examples = []
    with open(path) as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def check_format_consistency(examples: list[dict]) -> tuple[bool, dict]:
    """Check if examples use consistent tool call format.

    Format A (Code Mode): <function=execute_code><parameter=code>...</parameter></function>
    Format B (Bare): <tool_call>result = foo(...) (no function wrapper)

    Returns: (passed, details)
    """
    format_a_count = 0  # Code Mode
    format_b_count = 0  # Bare format
    mixed_examples = []

    for i, example in enumerate(examples):
        assistant_msg = None
        for msg in example.get("messages", []):
            if msg.get("role") == "assistant":
                assistant_msg = msg.get("content", "")
                break

        if not assistant_msg or "<tool_call>" not in assistant_msg:
            continue  # Skip direct answers

        has_format_a = "<function=execute_code>" in assistant_msg
        has_format_b = (
            "<tool_call>result = " in assistant_msg
            and "<function=execute_code>" not in assistant_msg
        )

        if has_format_a and has_format_b:
            mixed_examples.append(i)
        elif has_format_a:
            format_a_count += 1
        elif has_format_b:
            format_b_count += 1

    # FAIL if both formats present (gradient signal split)
    passed = not (format_a_count > 0 and format_b_count > 0) and not mixed_examples

    details = {
        "format_a": format_a_count,
        "format_b": format_b_count,
        "mixed": mixed_examples,
        "status": "CONSISTENT" if passed else "INCONSISTENT",
    }

    return passed, details


def classify_tool(assistant_msg: str) -> str:
    """Classify an assistant message by tool type.

    Args:
        assistant_msg: Assistant message content

    Returns:
        Tool name or "direct_answer" or "other"
    """
    if "<tool_call>" not in assistant_msg:
        return "direct_answer"

    # All 14 tools (11 typed + 3 core)
    all_tools = [
        # LSP Navigation
        "goto_definition",
        "find_references",
        "hover",
        "document_symbols",
        "workspace_symbols",
        # Quality Tools
        "typecheck",
        "ruff_check",
        "pytest_run",
        # Git Tools
        "git_status",
        "git_diff",
        "git_log",
        # Core Tools
        "read_file",
        "write_file",
        "run_command",
    ]

    # Check in order (most specific first)
    for tool in all_tools:
        if tool in assistant_msg:
            return tool

    return "other"


def check_shuffle_quality(examples: list[dict]) -> tuple[bool, dict]:
    """Check if examples are well-shuffled (not clustered by type).

    Returns: (passed, details)
    """
    # Extract tool types from examples
    tool_types = []
    for example in examples:
        assistant_msg = None
        for msg in example.get("messages", []):
            if msg.get("role") == "assistant":
                assistant_msg = msg.get("content", "")
                break

        if not assistant_msg:
            continue

        tool_types.append(classify_tool(assistant_msg))

    # Check distribution in first vs second half
    midpoint = len(tool_types) // 2
    first_half = Counter(tool_types[:midpoint])
    second_half = Counter(tool_types[midpoint:])

    # Calculate percentage of each type in first half vs total
    distributions = {}
    for tool_type in set(tool_types):
        total = first_half[tool_type] + second_half[tool_type]
        if total > 0:
            first_half_pct = (first_half[tool_type] / total) * 100
            distributions[tool_type] = first_half_pct

    # FAIL if any type is >90% in first half or <10% (indicates clustering)
    clustered = {
        k: v for k, v in distributions.items() if v > 90 or v < 10
    }
    passed = len(clustered) == 0

    details = {
        "distributions": distributions,
        "clustered": clustered,
        "status": "SHUFFLED" if passed else "CLUSTERED",
    }

    return passed, details


def check_balance(examples: list[dict]) -> tuple[bool, dict]:
    """Check if tool types are reasonably balanced.

    Returns: (passed, details)
    """
    tool_counts = Counter()
    for example in examples:
        assistant_msg = None
        for msg in example.get("messages", []):
            if msg.get("role") == "assistant":
                assistant_msg = msg.get("content", "")
                break

        if not assistant_msg:
            continue

        tool_counts[classify_tool(assistant_msg)] += 1

    total = sum(tool_counts.values())
    percentages = {k: (v / total) * 100 for k, v in tool_counts.items()}

    # WARN if any tool type is <5% of total
    underrepresented = {k: v for k, v in percentages.items() if v < 5.0}
    passed = len(underrepresented) == 0

    details = {
        "counts": dict(tool_counts),
        "percentages": percentages,
        "underrepresented": underrepresented,
        "total": total,
        "status": "BALANCED" if passed else "IMBALANCED",
    }

    return passed, details


def check_system_messages(examples: list[dict]) -> tuple[bool, dict]:
    """Check that examples have system messages consistently.

    Returns: (passed, details)
    """
    with_system = 0
    without_system = 0

    for example in examples:
        messages = example.get("messages", [])
        has_system = any(msg.get("role") == "system" for msg in messages)

        if has_system:
            with_system += 1
        else:
            without_system += 1

    total = with_system + without_system
    system_pct = (with_system / total * 100) if total > 0 else 0

    # WARN if <90% of examples have system messages
    passed = system_pct >= 90.0

    details = {
        "with_system": with_system,
        "without_system": without_system,
        "percentage": system_pct,
        "total": total,
        "status": "CONSISTENT" if passed else "INCONSISTENT",
    }

    return passed, details


def check_tag_validity(examples: list[dict]) -> tuple[bool, dict]:
    """Check that all tool call tags are properly closed.

    Returns: (passed, details)
    """
    unclosed = []

    for i, example in enumerate(examples):
        assistant_msg = None
        for msg in example.get("messages", []):
            if msg.get("role") == "assistant":
                assistant_msg = msg.get("content", "")
                break

        if not assistant_msg:
            continue

        # Check tag pairs
        issues = []
        if "<tool_call>" in assistant_msg:
            if assistant_msg.count("<tool_call>") != assistant_msg.count("</tool_call>"):
                issues.append("tool_call")

        if "<function=execute_code>" in assistant_msg:
            if assistant_msg.count("<function=execute_code>") != assistant_msg.count("</function>"):
                issues.append("function")

        if "<parameter=code>" in assistant_msg:
            if assistant_msg.count("<parameter=code>") != assistant_msg.count("</parameter>"):
                issues.append("parameter")

        if issues:
            unclosed.append({"index": i, "issues": issues})

    passed = len(unclosed) == 0

    details = {
        "unclosed": unclosed,
        "count": len(unclosed),
        "status": "VALID" if passed else "INVALID",
    }

    return passed, details


def main():
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/audit_training_data.py data/phase26_balanced/train.jsonl")
        sys.exit(1)

    data_path = Path(sys.argv[1])
    if not data_path.exists():
        print(f"Error: {data_path} does not exist")
        sys.exit(1)

    print(f"Auditing training data: {data_path}")
    print("=" * 80)

    # Load examples
    examples = load_examples(data_path)
    print(f"Loaded {len(examples)} examples\n")

    # Run checks
    checks = [
        ("Format Consistency", check_format_consistency),
        ("System Messages", check_system_messages),
        ("Shuffle Quality", check_shuffle_quality),
        ("Balance", check_balance),
        ("Tag Validity", check_tag_validity),
    ]

    all_passed = True
    for name, check_func in checks:
        passed, details = check_func(examples)
        all_passed = all_passed and passed

        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} {name}: {details['status']}")

        if name == "Format Consistency":
            print(f"   Format A (Code Mode): {details['format_a']} examples")
            print(f"   Format B (Bare): {details['format_b']} examples")
            if details['mixed']:
                print(f"   Mixed format examples: {details['mixed'][:5]}...")

        elif name == "System Messages":
            print(f"   With system message: {details['with_system']} ({details['percentage']:.1f}%)")
            print(f"   Without system message: {details['without_system']}")
            if not passed:
                print(f"   ⚠️  System message coverage below 90% threshold")

        elif name == "Shuffle Quality":
            if not passed:
                print(f"   Clustered types: {details['clustered']}")
            else:
                # Show sample of distribution
                sample = list(details['distributions'].items())[:3]
                for tool, pct in sample:
                    print(f"   {tool}: {pct:.1f}% in first half")

        elif name == "Balance":
            for tool, pct in sorted(details['percentages'].items(), key=lambda x: -x[1]):
                count = details['counts'][tool]
                print(f"   {tool}: {count} ({pct:.1f}%)")
            if details['underrepresented']:
                print(f"   ⚠️  Underrepresented: {list(details['underrepresented'].keys())}")

        elif name == "Tag Validity":
            if not passed:
                print(f"   Unclosed tags in {details['count']} examples")
                for item in details['unclosed'][:3]:
                    print(f"   - Example {item['index']}: {item['issues']}")

        print()

    # Summary
    print("=" * 80)
    if all_passed:
        print("✅ All checks PASSED - training data is ready")
        sys.exit(0)
    else:
        print("❌ Some checks FAILED - fix issues before training")
        sys.exit(1)


if __name__ == "__main__":
    main()
