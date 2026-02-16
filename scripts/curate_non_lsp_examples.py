#!/usr/bin/env python
"""Curate non-LSP training examples from Phase 22-26.

Current: 953 non-LSP examples
Target: ~400 best examples

Selection strategy:
- Phase 26 field access (120 examples) - keep all (most recent, critical patterns)
- Phase 23-24 typed tools (150 examples) - keep ~100 best
- Phase 22 Code Mode (683 examples) - keep ~200 best (core tool calling)

Output: data/phase26_curated_non_lsp/ in JSONL format
"""

import json
from pathlib import Path


def load_jsonl(file_path: Path) -> list[dict]:
    """Load examples from JSONL file."""
    examples = []
    if not file_path.exists():
        return examples

    with open(file_path) as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def save_jsonl(examples: list[dict], file_path: Path):
    """Save examples to JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")


def prioritize_examples(examples: list[dict]) -> list[dict]:
    """Prioritize examples by quality markers."""
    # Scoring criteria:
    # +10: Has field access (.error_count, .errors, .success, etc.)
    # +5: Has conditional logic (if result.success:)
    # +5: Has iteration (for error in result.errors:)
    # +3: Multi-line code
    # +2: Has tool call

    scored = []
    for ex in examples:
        score = 0
        content = ex["messages"][1]["content"]

        # Field access
        if any(field in content for field in [".error_count", ".errors", ".success", ".locations", ".references"]):
            score += 10

        # Conditional logic
        if "if result" in content:
            score += 5

        # Iteration
        if "for " in content and (" in result" in content or ".errors" in content):
            score += 5

        # Multi-line (more complex)
        if content.count("\n") >= 3:
            score += 3

        # Has tool call
        if "<tool_call>" in content:
            score += 2

        scored.append((score, ex))

    # Sort by score (descending) and return examples
    scored.sort(reverse=True, key=lambda x: x[0])
    return [ex for _, ex in scored]


def main():
    """Curate non-LSP examples."""
    print("Curating non-LSP training examples...")

    # Load all Phase 26 merged data (includes Phase 22-26 patterns)
    print("\n1. Loading Phase 26 merged examples...")
    train_examples = load_jsonl(Path("data/phase26_merged/train.jsonl"))
    valid_examples = load_jsonl(Path("data/phase26_merged/valid.jsonl"))
    all_examples = train_examples + valid_examples
    print(f"   Found {len(all_examples)} examples total")
    print(f"   (train: {len(train_examples)}, valid: {len(valid_examples)})")

    # Prioritize by quality
    print("\n2. Prioritizing examples by quality...")
    prioritized = prioritize_examples(all_examples)

    # Select top 400
    curated = prioritized[:400]
    print(f"   Selected top {len(curated)} examples")

    print(f"\n✓ Total curated: {len(curated)} examples")

    # Save
    output_dir = Path("data/phase26_curated_non_lsp")
    output_file = output_dir / "examples.jsonl"
    save_jsonl(curated, output_file)
    print(f"✓ Saved to {output_file}")

    # Statistics
    print("\nStatistics:")
    print("  Source: Phase 26 merged (Phase 22-26 patterns)")
    print(f"  Original: {len(all_examples)} examples")
    print(f"  Curated: {len(curated)} examples (top {len(curated)/len(all_examples)*100:.1f}%)")

    # Check field access rate
    tool_examples = [ex for ex in curated if "<tool_call>" in ex["messages"][1]["content"]]
    field_examples = [
        ex for ex in tool_examples
        if any(pattern in ex["messages"][1]["content"] for pattern in [".error_count", ".errors", ".success", "result."])
    ]
    field_rate = len(field_examples) / len(tool_examples) * 100 if tool_examples else 0
    print(f"  Field access rate: {field_rate:.1f}% ({len(field_examples)}/{len(tool_examples)})")


if __name__ == "__main__":
    main()
