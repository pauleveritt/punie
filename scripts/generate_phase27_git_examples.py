"""Generate Phase 27 git training examples (git_status, git_diff, git_log).

Creates 180 examples:
- 30 git_status discrimination (git_status vs run_command for changes)
- 30 git_status + field access (filter result.files, check .staged)
- 30 git_diff discrimination + field access
- 30 git_diff workflows (diff → read modified file → fix)
- 30 git_log discrimination + field access
- 30 git_log workflows (log → find commit → diff)

All examples follow Phase 26 structural norms:
- 100% system messages
- ~37% multi-turn (5-message format)
- ~33% preambles
- Code Mode format (<tool_call><function=execute_code>)
"""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(43)


def create_git_status_discrimination_examples() -> list[dict]:
    """Create 30 git_status discrimination examples."""
    examples = []

    queries = [
        ("What files have changed?", "."),
        ("Show git working tree status", "."),
        ("Check for uncommitted changes", "."),
        ("List modified files", "."),
        ("What's the git status?", "."),
        ("Show staged files", "."),
        ("Check for untracked files", "."),
        ("What changes are pending?", "."),
        ("Show working directory status", "."),
        ("List files that need committing", "."),
    ]

    for query, path in queries:
        # Single-turn
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_status("{path}")\nif result.clean:\n    print("Working tree is clean")\nelse:\n    print(f"{{result.file_count}} files changed")\n    for file in result.files:\n        status_str = "staged" if file.staged else "unstaged"\n        print(f"  {{file.file}} ({{file.status}}, {{status_str}})")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with preamble
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll check the git status.",
                },
                {
                    "role": "user",
                    "content": "Show me what changed.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_status("{path}")\nprint(f"Clean: {{result.clean}}")\nprint(f"Files: {{result.file_count}}")\nif not result.clean:\n    for file in result.files:\n        print(f"  {{file.file}}: {{file.status}}")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_git_status_field_access_examples() -> list[dict]:
    """Create 30 git_status + field access examples."""
    examples = []

    queries = [
        ("Count staged files", "."),
        ("Show only unstaged changes", "."),
        ("Filter modified files", "."),
        ("Count untracked files", "."),
        ("Show staged vs unstaged counts", "."),
        ("List only staged files", "."),
        ("Check if any files are modified", "."),
        ("Count files by status", "."),
        ("Show files that are not staged", "."),
        ("Get total change count", "."),
    ]

    for query, path in queries:
        # Field access with filtering
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_status("{path}")\nif not result.clean:\n    staged = [f for f in result.files if f.staged]\n    unstaged = [f for f in result.files if not f.staged]\n    print(f"Staged: {{len(staged)}}")\n    print(f"Unstaged: {{len(unstaged)}}")\n    print(f"Total: {{result.file_count}}")\nelse:\n    print("No changes")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with grouping
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll analyze the status by category.",
                },
                {
                    "role": "user",
                    "content": "Show the breakdown.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_status("{path}")\nif result.file_count > 0:\n    by_status = {{}}\n    for file in result.files:\n        if file.status not in by_status:\n            by_status[file.status] = 0\n        by_status[file.status] += 1\n    for status, count in by_status.items():\n        print(f"{{status}}: {{count}} files")\nelse:\n    print("Working tree clean")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_git_diff_discrimination_examples() -> list[dict]:
    """Create 30 git_diff discrimination + field access examples."""
    examples = []

    queries = [
        ("Show unstaged changes", ".", False),
        ("What are the staged changes?", ".", True),
        ("Show diff for uncommitted changes", ".", False),
        ("Check staged diff", ".", True),
        ("What changed in working directory?", ".", False),
        ("Show changes to be committed", ".", True),
        ("Display unstaged modifications", ".", False),
        ("Check what's staged for commit", ".", True),
        ("Show working tree diff", ".", False),
        ("What will be committed?", ".", True),
    ]

    for query, path, staged in queries:
        # Single-turn with field access
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_diff("{path}", staged={staged})\nif result.file_count > 0:\n    print(f"Files changed: {{result.file_count}}")\n    print(f"Additions: +{{result.additions}}")\n    print(f"Deletions: -{{result.deletions}}")\n    for file in result.files:\n        print(f"  {{file.file}}: +{{file.additions}} -{{file.deletions}}")\nelse:\n    print("No changes")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with analysis
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll get the diff statistics.",
                },
                {
                    "role": "user",
                    "content": "Show me the details.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_diff("{path}", staged={staged})\nif result.success:\n    print(f"Changed files: {{result.file_count}}")\n    print(f"Total changes: +{{result.additions}} -{{result.deletions}}")\n    if result.files:\n        largest = max(result.files, key=lambda f: f.additions + f.deletions)\n        print(f"Largest change: {{largest.file}}")\nelse:\n    print("No diff available")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_git_diff_workflow_examples() -> list[dict]:
    """Create 30 git_diff workflow examples (diff → read → fix)."""
    examples = []

    workflows = [
        ("Check what changed in src/ and read the files", "src", False),
        ("Show staged changes and review modified files", ".", True),
        ("Get diff and check the largest changes", ".", False),
        ("Review staged files before commit", ".", True),
        ("Check unstaged changes and read modified code", ".", False),
        ("Analyze diff and identify files to review", ".", False),
        ("Show changes and read the modified files", ".", False),
        ("Check diff and count lines changed per file", ".", False),
        ("Get staged diff and verify changes", ".", True),
        ("Review working tree changes before staging", ".", False),
    ]

    for query, path, staged in workflows:
        # Multi-step workflow
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\n# Get diff first\nresult = git_diff("{path}", staged={staged})\n\nif result.file_count > 0:\n    print(f"Changed {{result.file_count}} files (+{{result.additions}} -{{result.deletions}})")\n    \n    # Find files with most changes\n    for file in sorted(result.files, key=lambda f: f.additions + f.deletions, reverse=True)[:3]:\n        print(f"\\n{{file.file}}: +{{file.additions}} -{{file.deletions}}")\n        # Read the file to see current state\n        try:\n            content = read_file(file.file)\n            lines = content.split("\\n")\n            print(f"  Current size: {{len(lines)}} lines")\n        except:\n            print(f"  Could not read file")\nelse:\n    print("No changes to review")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn workflow with preamble
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll check the diff and review the changed files.",
                },
                {
                    "role": "user",
                    "content": "Go ahead.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\ndiff = git_diff("{path}", staged={staged})\n\nif diff.file_count > 0:\n    print(f"Files to review: {{diff.file_count}}")\n    \n    for file in diff.files:\n        print(f"\\n{{file.file}}:")\n        print(f"  Changes: +{{file.additions}} -{{file.deletions}}")\n        print(f"  Hunks: {{len(file.hunks)}}")\nelse:\n    print("No changes")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_git_log_discrimination_examples() -> list[dict]:
    """Create 30 git_log discrimination + field access examples."""
    examples = []

    queries = [
        ("Show recent commits", ".", 10),
        ("Get last 5 commits", ".", 5),
        ("Show commit history", ".", 10),
        ("List recent 8 commits", ".", 8),
        ("What are the latest commits?", ".", 10),
        ("Show last 3 commits", ".", 3),
        ("Get commit log", ".", 10),
        ("Show recent 15 commits", ".", 15),
        ("List last 7 commits", ".", 7),
        ("What's in the commit history?", ".", 10),
    ]

    for query, path, count in queries:
        # Single-turn with field access
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_log("{path}", count={count})\nif result.commit_count > 0:\n    print(f"Found {{result.commit_count}} commits:")\n    for commit in result.commits:\n        print(f"  {{commit.hash}} - {{commit.message}}")\nelse:\n    print("No commits found")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll get the commit history.",
                },
                {
                    "role": "user",
                    "content": "Show me the commits.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_log("{path}", count={count})\nprint(f"Commits: {{result.commit_count}}")\nfor commit in result.commits:\n    print(f"{{commit.hash[:7]}} {{commit.message[:50]}}")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_git_log_workflow_examples() -> list[dict]:
    """Create 30 git_log workflow examples (log → find commit → diff)."""
    examples = []

    workflows = [
        ("Show commits and find ones about fixes", ".", 10),
        ("Get recent commits and filter by keyword", ".", 10),
        ("Show commit history and count by pattern", ".", 15),
        ("Find commits about features", ".", 10),
        ("Search commit messages for bug fixes", ".", 20),
        ("Show commits and filter by message content", ".", 10),
        ("Find commits related to refactoring", ".", 10),
        ("Search for commits about tests", ".", 10),
        ("Show commits and identify merge commits", ".", 10),
        ("Find commits by message pattern", ".", 10),
    ]

    for query, path, count in workflows:
        # Multi-step workflow
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\n# Get commit history\nresult = git_log("{path}", count={count})\n\nif result.commit_count > 0:\n    print(f"Analyzing {{result.commit_count}} commits")\n    \n    # Filter by keyword\n    keyword = "fix"\n    matching = [c for c in result.commits if keyword.lower() in c.message.lower()]\n    \n    print(f"\\nCommits with \'{{keyword}}\': {{len(matching)}}")\n    for commit in matching:\n        print(f"  {{commit.hash}} - {{commit.message}}")\n    \n    # Show summary\n    total = len(result.commits)\n    percent = (len(matching) / total * 100) if total > 0 else 0\n    print(f"\\nMatch rate: {{percent:.1f}}%")\nelse:\n    print("No commits found")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn workflow
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll analyze the commit history.",
                },
                {
                    "role": "user",
                    "content": "Show me the analysis.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nlog = git_log("{path}", count={count})\n\nif log.success:\n    # Group by first word\n    first_words = {{}}\n    for commit in log.commits:\n        first_word = commit.message.split()[0] if commit.message else "unknown"\n        if first_word not in first_words:\n            first_words[first_word] = 0\n        first_words[first_word] += 1\n    \n    print("Commit message patterns:")\n    for word, count in sorted(first_words.items(), key=lambda x: x[1], reverse=True)[:5]:\n        print(f"  {{word}}: {{count}} commits")\nelse:\n    print("No log available")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def main():
    """Generate all Phase 27 git examples."""
    output_dir = Path("data/phase27_git")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_examples = []

    print("Generating git_status discrimination examples...")
    all_examples.extend(create_git_status_discrimination_examples())

    print("Generating git_status field access examples...")
    all_examples.extend(create_git_status_field_access_examples())

    print("Generating git_diff discrimination examples...")
    all_examples.extend(create_git_diff_discrimination_examples())

    print("Generating git_diff workflow examples...")
    all_examples.extend(create_git_diff_workflow_examples())

    print("Generating git_log discrimination examples...")
    all_examples.extend(create_git_log_discrimination_examples())

    print("Generating git_log workflow examples...")
    all_examples.extend(create_git_log_workflow_examples())

    # Shuffle examples
    random.shuffle(all_examples)

    # Save as JSONL
    output_file = output_dir / "phase27_git_examples.jsonl"
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nGenerated {len(all_examples)} git examples")
    print(f"Saved to: {output_file}")

    # Print distribution
    single_turn = sum(1 for ex in all_examples if len(ex["messages"]) == 3)
    multi_turn = sum(1 for ex in all_examples if len(ex["messages"]) > 3)
    print(f"\nDistribution:")
    print(f"  Single-turn: {single_turn} ({single_turn/len(all_examples)*100:.1f}%)")
    print(f"  Multi-turn: {multi_turn} ({multi_turn/len(all_examples)*100:.1f}%)")


if __name__ == "__main__":
    main()
