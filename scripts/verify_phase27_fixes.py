#!/usr/bin/env python3
"""Verify that all Phase 27 data fixes were applied correctly.

Comprehensive verification covering:
1. No quote corruption in non-Result tool responses
2. All Result objects have quotes converted
3. No author=None or date=None in GitCommit objects
4. All git_log responses are unique
5. Author diversity across git_log examples
6. No JSON-format tool calls remain
7. Original fixes still intact (no duplicates, leakage, role:'tool')
8. Git log keywords match user queries
9. Orphaned tool calls detection (informational)
"""

import json
import re
from pathlib import Path
from collections import Counter


# Known Result types that should have single-quoted field values
RESULT_TYPES = {
    "GotoDefinitionResult", "FindReferencesResult", "TypeCheckResult",
    "RuffResult", "TestResult", "HoverResult", "DocumentSymbolsResult",
    "WorkspaceSymbolsResult", "GitLogResult", "GitStatusResult", "GitDiffResult",
}


def verify_no_quote_corruption(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify non-Result tool responses don't have corrupted quotes.

    For tool responses that are NOT Result objects (raw text), ensure we didn't
    accidentally convert double quotes to single quotes in HTML attributes.
    Looks for common HTML attribute patterns with single quotes.
    """
    corruptions = []

    # Regex pattern matching common HTML attributes with single quotes (indicates corruption)
    html_attr_pattern = re.compile(
        r'(?:class|id|style|href|src|title|alt|type|name|value|action|method|'
        r'target|rel|role|placeholder|for|data-\w+|aria-\w+)=\'[^\']*\''
    )

    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        for i, ex in enumerate(examples):
            messages = ex.get("messages", [])
            for msg in messages:
                content = msg.get("content", "")
                if "<tool_response>" not in content:
                    continue

                # Extract content between <tool_response>...</tool_response>
                inner = content.split("<tool_response>", 1)[1].split("</tool_response>", 1)[0].strip()

                # Skip if this is a Result object (those SHOULD have single quotes)
                if any(inner.startswith(rt + "(") for rt in RESULT_TYPES):
                    continue

                # For raw text responses, check for HTML attribute patterns with single quotes
                # These would indicate incorrect quote conversion
                if html_attr_pattern.search(inner):
                    corruptions.append((filepath.name, i + 1, inner[:100]))

    if not corruptions:
        return True, "✅ No quote corruption in non-Result tool responses"
    else:
        return False, f"❌ Found {len(corruptions)} corrupted non-Result responses: {corruptions[:3]}"


def verify_result_quotes_converted(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify all Result objects have double quotes converted to single quotes.

    This is the positive check: ensure Result objects DID get fixed.
    """
    unconverted = []

    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        for i, ex in enumerate(examples):
            messages = ex.get("messages", [])
            for msg in messages:
                content = msg.get("content", "")
                if "<tool_response>" not in content:
                    continue

                # Extract content between <tool_response>...</tool_response>
                inner = content.split("<tool_response>", 1)[1].split("</tool_response>", 1)[0].strip()

                # Only check Result objects
                if not any(inner.startswith(rt + "(") for rt in RESULT_TYPES):
                    continue

                # Check for remaining double-quoted field values
                # Pattern: word="value" (should have been converted to word='value')
                # Exception: values containing single quotes keep double quotes (Pydantic behavior)
                double_quoted = re.finditer(r'\w+="([^"]*)"', inner)
                for m in double_quoted:
                    if "'" not in m.group(1):
                        # This value has no single quotes, so should have been converted
                        unconverted.append((filepath.name, i + 1, inner[:100]))
                        break

    if not unconverted:
        return True, "✅ All Result objects have quotes converted to single quotes"
    else:
        return False, f"❌ Found {len(unconverted)} Result objects with unconverted double quotes: {unconverted[:3]}"


def verify_no_none_authors(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify no GitCommit objects in tool responses have author=None or date=None.

    Only checks content within <tool_response> tags, not assistant code that
    might legitimately reference these fields.
    """
    none_authors = []

    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        for i, ex in enumerate(examples):
            messages = ex.get("messages", [])
            for msg in messages:
                content = msg.get("content", "")
                if "<tool_response>" not in content:
                    continue
                # Extract only the tool_response inner content
                inner = content.split("<tool_response>", 1)[1].split("</tool_response>", 1)[0]
                if "GitCommit(" in inner and ("author=None" in inner or "date=None" in inner):
                    none_authors.append((filepath.name, i + 1))

    if not none_authors:
        return True, "✅ No GitCommit objects with author=None or date=None"
    else:
        return False, f"❌ Found {len(none_authors)} GitCommit objects with None values: {none_authors[:5]}"


def verify_git_log_uniqueness(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify all git_log tool responses are unique (no hardcoded count)."""
    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        git_log_responses = []
        for ex in examples:
            messages = ex.get("messages", [])
            # Check if this has git_log tool call
            has_git_log = any(
                msg.get("role") == "assistant" and "git_log(" in msg.get("content", "")
                for msg in messages
            )
            if has_git_log:
                # Find the tool response
                tool_response = next(
                    (msg.get("content", "") for msg in messages
                     if msg.get("role") == "user" and "<tool_response>" in msg.get("content", "")),
                    None
                )
                if tool_response:
                    git_log_responses.append(tool_response)

        unique_count = len(set(git_log_responses))
        total_count = len(git_log_responses)

        if total_count > 0 and unique_count != total_count:
            return False, f"❌ {filepath.name}: {unique_count} unique out of {total_count} git_log responses (expected all unique)"

    return True, f"✅ All git_log responses are unique in both files"


def verify_author_diversity(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify git_log examples have diverse first authors (>= 3 different)."""
    checked_files = []

    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        first_authors = []
        for ex in examples:
            messages = ex.get("messages", [])
            # Check if this has git_log tool call
            has_git_log = any(
                msg.get("role") == "assistant" and "git_log(" in msg.get("content", "")
                for msg in messages
            )
            if has_git_log:
                # Find the tool response
                tool_response = next(
                    (msg.get("content", "") for msg in messages
                     if msg.get("role") == "user" and "<tool_response>" in msg.get("content", "")),
                    None
                )
                if tool_response and "GitCommit(hash=" in tool_response:
                    # Extract first author
                    if "author='" in tool_response:
                        author = tool_response.split("author='", 1)[1].split("'", 1)[0]
                        first_authors.append(author)

        if not first_authors:
            continue

        checked_files.append(filepath.name)
        unique_count = len(set(first_authors))

        if unique_count < 3:
            author_counts = Counter(first_authors)
            return False, f"❌ {filepath.name}: Only {unique_count} different first authors (expected >= 3): {dict(author_counts)}"

    if not checked_files:
        return True, "✅ No git_log responses found in either file (nothing to check)"

    files_str = " and ".join(checked_files)
    return True, f"✅ Sufficient author diversity (>= 3 different) in {files_str}"


def verify_no_json_format(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify no JSON-format tool calls remain."""
    json_format_count = 0

    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        for ex in examples:
            messages = ex.get("messages", [])
            for msg in messages:
                content = msg.get("content", "")
                if msg.get("role") == "assistant" and '"name":' in content and '"arguments":' in content:
                    json_format_count += 1

    if json_format_count == 0:
        return True, "✅ No JSON-format tool calls found in either file"
    else:
        return False, f"❌ Found {json_format_count} JSON-format tool calls"


def verify_original_fixes(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify original fixes are still in place (dedupe, leakage, role fixes).

    Uses canonical JSON comparison with sorted keys to match fix script.
    """
    issues = []

    # Load examples as JSON objects for canonical comparison
    with open(train_file) as f:
        train_examples = [json.loads(line) for line in f]

    with open(valid_file) as f:
        valid_examples = [json.loads(line) for line in f]

    # Check train duplicates (using canonical JSON)
    train_canonical = [json.dumps(ex, sort_keys=True) for ex in train_examples]
    train_dupes = len(train_canonical) - len(set(train_canonical))
    if train_dupes > 0:
        issues.append(f"train has {train_dupes} duplicates")

    # Check valid duplicates (using canonical JSON)
    valid_canonical = [json.dumps(ex, sort_keys=True) for ex in valid_examples]
    valid_dupes = len(valid_canonical) - len(set(valid_canonical))
    if valid_dupes > 0:
        issues.append(f"valid has {valid_dupes} duplicates")

    # Check train/valid leakage (using canonical JSON)
    train_set = set(train_canonical)
    valid_set = set(valid_canonical)
    leakage = len(train_set & valid_set)
    if leakage > 0:
        issues.append(f"train/valid leakage: {leakage}")

    # Check role:"tool" messages
    for filepath, examples in [(train_file, train_examples), (valid_file, valid_examples)]:
        tool_roles = sum(
            1 for ex in examples
            for msg in ex.get("messages", [])
            if msg.get("role") == "tool"
        )
        if tool_roles > 0:
            issues.append(f"{filepath.name} has {tool_roles} role:'tool' messages")

    if not issues:
        return True, "✅ All original fixes still in place (no duplicates, leakage, or role:'tool')"
    else:
        return False, f"❌ Original fix regressions: {', '.join(issues)}"


def verify_git_log_keywords(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Verify git_log keyword assignments match user queries."""
    mismatches = []

    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        for i, ex in enumerate(examples):
            messages = ex.get("messages", [])

            # Find assistant messages with keyword = "..."
            for msg in messages:
                if msg.get("role") != "assistant":
                    continue
                content = msg.get("content", "")
                kw_match = re.search(r'keyword\s*=\s*["\']([^"\']*)["\']', content)
                if not kw_match:
                    continue

                keyword = kw_match.group(1)

                # Find the user query (not a tool response)
                user_query = next(
                    (m["content"] for m in messages
                     if m["role"] == "user" and "<tool_response>" not in m.get("content", "")),
                    "",
                )

                # Verify keyword appears in the user query
                if keyword.lower() not in user_query.lower():
                    mismatches.append((filepath.name, i + 1, keyword, user_query[:80]))

    if not mismatches:
        return True, "✅ All git_log keywords match user queries"
    else:
        details = "; ".join(f"{f}:{n} keyword='{k}' not in query" for f, n, k, _ in mismatches[:3])
        return False, f"❌ Found {len(mismatches)} keyword mismatches: {details}"


KNOWN_TOOLS = [
    "git_log", "git_status", "git_diff",
    "hover", "goto_definition", "find_references",
    "document_symbols", "workspace_symbols",
    "typecheck", "ruff_check", "pytest_run",
    "execute_code",
]


def verify_no_orphaned_tool_calls(train_file: Path, valid_file: Path) -> tuple[bool, str]:
    """Report multi-turn examples that end with a tool call but no response (informational)."""
    orphaned_count = 0
    total_multi_turn = 0

    for filepath in [train_file, valid_file]:
        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        for ex in examples:
            messages = ex.get("messages", [])
            if len(messages) <= 2:
                continue

            # Check if last message is an assistant tool call with no subsequent tool response
            last_msg = messages[-1]
            if last_msg.get("role") == "assistant":
                content = last_msg.get("content", "")
                # Detect tool calls using known tool names
                has_tool_call = (
                    "<tool_call>" in content
                    or any(f"{tool}(" in content for tool in KNOWN_TOOLS)
                )
                if has_tool_call:
                    total_multi_turn += 1
                    orphaned_count += 1

    if orphaned_count == 0:
        return True, "✅ No orphaned tool calls found"
    else:
        return True, f"⚠️  {orphaned_count} examples end with tool call but no response (pre-existing, informational)"


def main():
    base_dir = Path("data/phase27_cleaned")
    train_file = base_dir / "train.jsonl"
    valid_file = base_dir / "valid.jsonl"

    print("🔍 Verifying Phase 27 data fixes (comprehensive suite)...\n")

    checks = [
        ("1. No quote corruption (non-Result)", verify_no_quote_corruption(train_file, valid_file)),
        ("2. Result quotes converted", verify_result_quotes_converted(train_file, valid_file)),
        ("3. No None authors/dates", verify_no_none_authors(train_file, valid_file)),
        ("4. Git log uniqueness", verify_git_log_uniqueness(train_file, valid_file)),
        ("5. Author diversity", verify_author_diversity(train_file, valid_file)),
        ("6. No JSON-format calls", verify_no_json_format(train_file, valid_file)),
        ("7. Original fixes intact", verify_original_fixes(train_file, valid_file)),
        ("8. Git log keywords match queries", verify_git_log_keywords(train_file, valid_file)),
        ("9. Orphaned tool calls", verify_no_orphaned_tool_calls(train_file, valid_file)),
    ]

    all_passed = True
    for name, (passed, message) in checks:
        print(f"{name}: {message}")
        if not passed:
            all_passed = False

    print(f"\n{'✅ All 9 checks passed!' if all_passed else '❌ Some checks failed'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
