#!/usr/bin/env python3
"""
Fix Phase 27 data issues found in audit.

Fixes:
1. Deduplicate exact-duplicate lines
2. Fix double-wrapped tool responses (role:"tool" → role:"user")
3. Rebuild 10 corrupted git_log tool responses from original source
4. Fix quote style (double quotes → single quotes in tool response content)
5. Remove train/valid leakage

Processes data/phase27_cleaned/{train,valid}.jsonl in-place.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def fix_quote_style(content: str) -> str:
    """Convert double-quoted field values to single-quoted in tool result repr strings.

    Matches Pydantic's __repr__() output at inference time.
    Handles all result types: GitCommit, GitLogResult, TypeCheckResult, etc.

    Keeps double quotes when the value contains single quotes (matching Pydantic behavior).
    """
    pattern = r'(\w+)="([^"]*)"'

    def replace_quotes(match):
        field = match.group(1)
        value = match.group(2)
        # Match Pydantic repr: use single quotes unless value contains single quotes
        if "'" in value:
            return match.group(0)  # keep double quotes (Pydantic behavior)
        return f"{field}='{value}'"

    return re.sub(pattern, replace_quotes, content)


def enrich_git_commits(content: str, seed: int = 0) -> str:
    """Add author and date to ALL GitCommit objects in a tool response.

    Fixes the bug where only the first commit was enriched.
    Args:
        seed: Offset for cross-example diversity (based on user query hash)
    """
    # Pattern to match GitCommit objects
    # Look for: GitCommit(hash='...', message='...', author=None, date=None)
    pattern = r"GitCommit\(hash='([^']+)',\s*message='([^']+)',\s*author=None,\s*date=None\)"

    # Sample authors and dates for diversity
    authors = [
        "Alex Johnson <alex@example.com>",
        "Sarah Chen <sarah@example.com>",
        "Michael Brown <michael@example.com>",
        "Emma Davis <emma@example.com>",
        "David Wilson <david@example.com>",
    ]
    dates = [
        "2026-02-10 13:25:15",
        "2026-02-09 09:45:30",
        "2026-02-08 16:20:45",
        "2026-02-07 11:15:00",
        "2026-02-06 14:30:25",
    ]

    commit_index = seed  # Start at different position per example

    def replace_commit(match):
        nonlocal commit_index
        hash_val = match.group(1)
        message = match.group(2)
        author = authors[commit_index % len(authors)]
        date = dates[commit_index % len(dates)]
        commit_index += 1

        return f"GitCommit(hash='{hash_val}', message='{message}', author='{author}', date='{date}')"

    return re.sub(pattern, replace_commit, content)


def load_original_git_log_examples() -> list[dict[str, Any]]:
    """Load the 10 original git_log examples (lines 51-60) from phase27_tool_responses."""
    original_file = Path("data/phase27_tool_responses/train.jsonl")

    if not original_file.exists():
        raise FileNotFoundError(f"Original source file not found: {original_file}")

    with open(original_file) as f:
        lines = f.readlines()

    # Lines 51-60 in human numbering = indices 50-59
    git_log_examples = []
    for i in range(50, 60):
        if i < len(lines):
            git_log_examples.append(json.loads(lines[i]))

    return git_log_examples


def is_git_log_example(example: dict[str, Any]) -> bool:
    """Check if this is a git_log example based on the assistant message content."""
    messages = example.get("messages", [])

    for msg in messages:
        if msg.get("role") == "assistant" and "git_log(" in msg.get("content", ""):
            return True

    return False


def has_json_format_tool_call(example: dict[str, Any]) -> bool:
    """Check if example uses old JSON-format tool calls instead of XML."""
    messages = example.get("messages", [])

    for msg in messages:
        content = msg.get("content", "")
        # JSON format has both "name": and "arguments": in the same message
        if msg.get("role") == "assistant" and '"name":' in content and '"arguments":' in content:
            return True

    return False


QUERY_KEYWORD_MAP = {
    "refactor": "refactor",
    "test": "test",
    "feature": "feature",
    "merge": "merge",
    "bug": "bug",
    "fix": "fix",
    "pattern": "pattern",
    "filter": "filter",
    "content": "content",
    "config": "config",
    "deploy": "deploy",
    "update": "update",
    "add": "add",
    "remove": "remove",
    "clean": "clean",
}


def fix_git_log_keyword(messages: list[dict[str, Any]]) -> None:
    """Replace hardcoded keyword='fix' with query-appropriate keyword.

    Mutates messages in place.
    """
    # Find the user query (not the tool response)
    user_query = next(
        (m["content"] for m in messages
         if m["role"] == "user" and "<tool_response>" not in m.get("content", "")),
        "",
    )

    # Find the best matching keyword from the user query
    query_lower = user_query.lower()
    keyword = "fix"  # default fallback
    for term, kw in QUERY_KEYWORD_MAP.items():
        if term in query_lower:
            keyword = kw
            break

    # Only replace if the keyword is different from "fix"
    if keyword == "fix":
        return

    # Replace in assistant messages (handle both double and single quotes)
    for msg in messages:
        if msg["role"] == "assistant":
            content = msg.get("content", "")
            if 'keyword = "fix"' in content:
                msg["content"] = content.replace('keyword = "fix"', f'keyword = "{keyword}"')
            elif "keyword = 'fix'" in content:
                msg["content"] = content.replace("keyword = 'fix'", f"keyword = '{keyword}'")


# Known Result types that should have quote conversion applied
RESULT_TYPES = {
    "GotoDefinitionResult", "FindReferencesResult", "TypeCheckResult",
    "RuffResult", "TestResult", "HoverResult", "DocumentSymbolsResult",
    "WorkspaceSymbolsResult", "GitLogResult", "GitStatusResult", "GitDiffResult",
}


def fix_example(example: dict[str, Any], original_git_logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Fix all issues in a single example.

    - Fix double-wrapped tool responses (role:"tool" → role:"user")
    - Restore corrupted git_log examples from original source
    - Fix quote style in structured Result objects only (not raw text)
    """
    messages = example["messages"]

    # Fix hardcoded keyword="fix" in git_log examples
    fix_git_log_keyword(messages)

    # Check if this is a corrupted git_log example
    is_git_log = is_git_log_example(example)

    # If it's a git_log example, try to restore from original
    if is_git_log:
        # Find matching original example by USER QUERY (not assistant content)
        # This fixes the bug where multiple examples had identical tool_call code
        for orig in original_git_logs:
            # Find the user query in both examples
            orig_user = next((m for m in orig["messages"] if m["role"] == "user" and "<tool_response>" not in m.get("content", "")), None)
            our_user = next((m for m in messages if m["role"] == "user" and "<tool_response>" not in m.get("content", "")), None)

            if orig_user and our_user and orig_user["content"] == our_user["content"]:
                # Found a match by user query - use the original tool response
                orig_tool = next((m for m in orig["messages"] if m["role"] == "tool"), None)
                if orig_tool:
                    # Find and replace the tool/user message (first one after the assistant)
                    for i, msg in enumerate(messages):
                        if msg["role"] in ("tool", "user") and i > 0 and messages[i-1]["role"] == "assistant":
                            # This is the tool response message - replace it
                            messages[i] = {
                                "role": "user",
                                "content": orig_tool["content"]
                            }
                            break
                    break

    # Get user query for diversity seed (deterministic)
    our_user = next((m for m in messages if m["role"] == "user" and "<tool_response>" not in m.get("content", "")), None)
    seed = int(hashlib.md5(our_user["content"].encode()).hexdigest(), 16) % 5 if our_user else 0  # modulo 5 for 5 authors

    # Fix all messages
    for msg in messages:
        content = msg.get("content", "")

        # Fix 1: Double-wrapped tool responses
        # If role is "tool" and content has <tool_response>, change role to "user"
        if msg["role"] == "tool" and "<tool_response>" in content:
            msg["role"] = "user"

        # Fix 2: Quote style - ONLY for structured Result objects, not raw text
        if "<tool_response>" in content:
            # Extract content between <tool_response>...</tool_response>
            parts = content.split("<tool_response>", 1)
            inner_and_rest = parts[1].split("</tool_response>", 1)
            raw_inner = inner_and_rest[0]
            inner = raw_inner.strip()

            # Only apply quote fixes if this is a structured Result object
            if any(inner.startswith(rt + "(") for rt in RESULT_TYPES):
                # Capture original whitespace prefix/suffix
                prefix = raw_inner[: len(raw_inner) - len(raw_inner.lstrip())]
                suffix = raw_inner[len(raw_inner.rstrip()) :]

                # Apply fix_quote_style only to the inner content, then reassemble
                fixed_inner = fix_quote_style(inner)
                # Then enrich git commits if present
                if "GitCommit(" in fixed_inner:
                    fixed_inner = enrich_git_commits(fixed_inner, seed=seed)
                content = parts[0] + "<tool_response>" + prefix + fixed_inner + suffix + "</tool_response>" + inner_and_rest[1]
                msg["content"] = content

    return example


def process_file(filepath: Path, original_git_logs: list[dict[str, Any]]) -> tuple[list[dict], int, int, int, int]:
    """Process a JSONL file: deduplicate, filter JSON-format, fix issues, return examples and counts.

    Returns:
        (examples, original_count, duplicate_count, json_format_count, fixed_role_count)
    """
    with open(filepath) as f:
        lines = f.readlines()

    original_count = len(lines)

    # Step 1: Deduplicate (keep first occurrence, using canonical JSON)
    seen = set()
    deduplicated = []
    duplicate_count = 0

    for line in lines:
        line = line.strip()
        example = json.loads(line)
        canonical = json.dumps(example, sort_keys=True)
        if canonical in seen:
            duplicate_count += 1
            continue
        seen.add(canonical)
        deduplicated.append(example)

    # Step 2: Filter out JSON-format tool calls (old format, conflicts with XML)
    filtered = []
    json_format_count = 0

    for example in deduplicated:
        if has_json_format_tool_call(example):
            json_format_count += 1
        else:
            filtered.append(example)

    # Step 3: Fix each example
    fixed_role_count = 0
    fixed_examples = []

    for example in filtered:
        # Count role:"tool" messages before fixing
        before_tool_count = sum(1 for m in example["messages"] if m["role"] == "tool")

        fixed = fix_example(example, original_git_logs)
        fixed_examples.append(fixed)

        # Count role:"tool" messages after fixing
        after_tool_count = sum(1 for m in fixed["messages"] if m["role"] == "tool")

        fixed_role_count += (before_tool_count - after_tool_count)

    return fixed_examples, original_count, duplicate_count, json_format_count, fixed_role_count


def remove_leakage(train_examples: list[dict], valid_examples: list[dict]) -> tuple[list[dict], int]:
    """Remove any valid examples that appear in train.

    Returns:
        (cleaned_valid_examples, leakage_count)
    """
    # Create set of train examples as JSON strings for exact matching
    train_set = {json.dumps(ex, sort_keys=True) for ex in train_examples}

    cleaned_valid = []
    leakage_count = 0

    for ex in valid_examples:
        ex_str = json.dumps(ex, sort_keys=True)
        if ex_str in train_set:
            leakage_count += 1
        else:
            cleaned_valid.append(ex)

    return cleaned_valid, leakage_count


def main():
    """Main execution."""
    base_dir = Path("data/phase27_cleaned")
    train_file = base_dir / "train.jsonl"
    valid_file = base_dir / "valid.jsonl"

    print("🔧 Fixing Phase 27 data issues...\n")

    # Load original git_log examples
    print("📥 Loading original git_log examples...")
    original_git_logs = load_original_git_log_examples()
    print(f"   Loaded {len(original_git_logs)} original git_log examples\n")

    # Process train.jsonl
    print("🔄 Processing train.jsonl...")
    train_examples, train_orig, train_dupes, train_json_fmt, train_roles = process_file(train_file, original_git_logs)
    print(f"   Original: {train_orig} lines")
    print(f"   Duplicates removed: {train_dupes}")
    print(f"   JSON-format tool calls removed: {train_json_fmt}")
    print(f"   Roles fixed: {train_roles}")
    print(f"   After cleanup: {len(train_examples)} examples\n")

    # Process valid.jsonl
    print("🔄 Processing valid.jsonl...")
    valid_examples, valid_orig, valid_dupes, valid_json_fmt, valid_roles = process_file(valid_file, original_git_logs)
    print(f"   Original: {valid_orig} lines")
    print(f"   Duplicates removed: {valid_dupes}")
    print(f"   JSON-format tool calls removed: {valid_json_fmt}")
    print(f"   Roles fixed: {valid_roles}")
    print(f"   After cleanup: {len(valid_examples)} examples\n")

    # Remove train/valid leakage
    print("🔍 Checking for train/valid leakage...")
    valid_examples, leakage_count = remove_leakage(train_examples, valid_examples)
    print(f"   Leakage removed: {leakage_count}")
    print(f"   Final valid: {len(valid_examples)} examples\n")

    # Write back
    print("💾 Writing fixed data...")
    with open(train_file, "w") as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + "\n")
    print(f"   train.jsonl: {len(train_examples)} examples")

    with open(valid_file, "w") as f:
        for ex in valid_examples:
            f.write(json.dumps(ex) + "\n")
    print(f"   valid.jsonl: {len(valid_examples)} examples\n")

    # Summary
    print("✅ Summary:")
    print(f"   Total duplicates removed: {train_dupes + valid_dupes}")
    print(f"   Total JSON-format tool calls removed: {train_json_fmt + valid_json_fmt}")
    print(f"   Total roles fixed: {train_roles + valid_roles}")
    print(f"   Train/valid leakage removed: {leakage_count}")
    print(f"   Final dataset: {len(train_examples)} train + {len(valid_examples)} valid = {len(train_examples) + len(valid_examples)} total")


if __name__ == "__main__":
    main()
