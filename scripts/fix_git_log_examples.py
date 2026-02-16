"""Fix git_log training examples to include author and date fields."""

import json
import random
from pathlib import Path

# Realistic author names for variety
AUTHORS = [
    "Paul Everitt <paul@example.com>",
    "John Doe <john@example.com>",
    "Jane Smith <jane@example.com>",
    "Alex Johnson <alex@example.com>",
    "Sarah Williams <sarah@example.com>",
]

# Date range: last 3 months
DATES = [
    "2026-02-15 14:30:22",
    "2026-02-14 10:15:45",
    "2026-02-13 16:20:10",
    "2026-02-12 09:45:30",
    "2026-02-11 11:00:00",
    "2026-02-10 13:25:15",
    "2026-01-28 15:40:50",
    "2026-01-20 08:30:25",
    "2026-01-15 17:10:40",
    "2026-01-10 12:55:30",
    "2025-12-20 10:20:15",
    "2025-12-15 14:45:20",
]


def fix_git_commit(commit_str: str) -> str:
    """Replace author=None, date=None with realistic values."""
    if "author=None, date=None" not in commit_str:
        return commit_str

    # Extract hash and message from GitCommit string
    # Example: GitCommit(hash="aaa1111", message="feat: add git integration", author=None, date=None)
    import re

    match = re.search(
        r'GitCommit\(hash="([^"]+)", message="([^"]+)", author=None, date=None\)',
        commit_str,
    )

    if not match:
        return commit_str

    hash_val = match.group(1)
    message = match.group(2)

    # Assign random but consistent author and date
    author = random.choice(AUTHORS)
    date = random.choice(DATES)

    # Build new GitCommit string
    return f'GitCommit(hash="{hash_val}", message="{message}", author="{author}", date="{date}")'


def process_file(input_path: Path, output_path: Path) -> tuple[int, int]:
    """Process a JSONL file and fix git_log examples.

    Returns:
        Tuple of (total_examples, fixed_examples)
    """
    total = 0
    fixed = 0

    with input_path.open() as f_in, output_path.open("w") as f_out:
        for line in f_in:
            total += 1
            data = json.loads(line)

            # Convert to JSON string for pattern matching
            original = json.dumps(data)

            # Check if this example contains git_log responses with author=None
            if "author=None, date=None" in original:
                # Fix each GitCommit in the JSON
                for msg in data.get("messages", []):
                    content = msg.get("content", "")
                    if "author=None, date=None" in content:
                        msg["content"] = fix_git_commit(content)
                        fixed += 1

            # Write the (possibly modified) example
            f_out.write(json.dumps(data) + "\n")

    return total, fixed


def main():
    """Fix git_log examples in both train and valid files."""
    data_dir = Path("data/phase27_cleaned")

    print("Fixing git_log training examples...")
    print()

    for split in ["train", "valid"]:
        input_file = data_dir / f"{split}.jsonl"
        output_file = data_dir / f"{split}.jsonl.fixed"

        if not input_file.exists():
            print(f"⚠️  {split}.jsonl not found, skipping")
            continue

        total, fixed = process_file(input_file, output_file)

        print(f"✅ {split}.jsonl: {total} examples, {fixed} fixes applied")

        # Replace original with fixed version
        output_file.replace(input_file)
        print(f"   Replaced {input_file}")
        print()

    # Verify the fix
    print("Verification:")
    result = (
        Path("data/phase27_cleaned/train.jsonl")
        .read_text()
        .count("author=None, date=None")
    )
    print(f"  Remaining 'author=None' in train.jsonl: {result}")

    if result == 0:
        print("\n🎉 All git_log examples successfully updated!")
    else:
        print(f"\n⚠️  Warning: {result} examples still have author=None")


if __name__ == "__main__":
    main()
