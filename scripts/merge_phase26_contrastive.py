#!/usr/bin/env python3
"""Merge Phase 26 balanced data with contrastive LSP examples.

Creates a new training dataset:
- 800 examples from Phase 26 balanced (field access + LSP + non-LSP)
- 80 contrastive examples (explicit LSP vs grep discrimination)
- Total: 880 examples

Split: 90/10 train/valid
"""

import json
import random
from pathlib import Path


def load_jsonl(file_path: Path) -> list[dict]:
    """Load examples from JSONL file."""
    examples = []
    with file_path.open() as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def save_jsonl(examples: list[dict], file_path: Path) -> None:
    """Save examples to JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")


def main():
    """Merge datasets and create train/valid split."""
    print("Loading Phase 26 balanced data...")
    balanced_train = load_jsonl(Path("data/phase26_balanced/train.jsonl"))
    balanced_valid = load_jsonl(Path("data/phase26_balanced/valid.jsonl"))
    print(f"  Loaded {len(balanced_train)} train + {len(balanced_valid)} valid = {len(balanced_train) + len(balanced_valid)} total")

    print("\nLoading contrastive examples...")
    contrastive = load_jsonl(Path("data/phase26_contrastive/examples.jsonl"))
    print(f"  Loaded {contrastive} contrastive examples")

    # Merge all examples
    all_examples = balanced_train + balanced_valid + contrastive
    print(f"\nTotal examples before shuffle: {len(all_examples)}")

    # Shuffle to prevent clustering
    random.seed(42)
    random.shuffle(all_examples)
    print("✓ Shuffled")

    # Split 90/10 train/valid
    split_idx = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_idx]
    valid_examples = all_examples[split_idx:]

    print(f"\nSplit:")
    print(f"  Train: {len(train_examples)} examples")
    print(f"  Valid: {len(valid_examples)} examples")

    # Save merged dataset
    output_dir = Path("data/phase26_contrastive_merged")
    save_jsonl(train_examples, output_dir / "train.jsonl")
    save_jsonl(valid_examples, output_dir / "valid.jsonl")

    print(f"\n✓ Saved to: {output_dir}")

    # Analyze distribution
    print("\nAnalyzing tool distribution in training data...")

    def count_tool_usage(examples: list[dict]) -> dict[str, int]:
        """Count how many examples use each tool."""
        counts = {}
        for ex in examples:
            content = str(ex)
            if "goto_definition" in content:
                counts["goto_definition"] = counts.get("goto_definition", 0) + 1
            if "find_references" in content:
                counts["find_references"] = counts.get("find_references", 0) + 1
            if "typecheck" in content:
                counts["typecheck"] = counts.get("typecheck", 0) + 1
            if "ruff_check" in content:
                counts["ruff_check"] = counts.get("ruff_check", 0) + 1
            if "pytest_run" in content:
                counts["pytest_run"] = counts.get("pytest_run", 0) + 1
            if 'run_command("grep"' in content or "run_command('grep'" in content:
                counts["grep"] = counts.get("grep", 0) + 1
            if "read_file" in content:
                counts["read_file"] = counts.get("read_file", 0) + 1
        return counts

    train_tools = count_tool_usage(train_examples)
    total_train = len(train_examples)

    print("\nTool usage in training data:")
    for tool, count in sorted(train_tools.items(), key=lambda x: -x[1]):
        pct = (count / total_train) * 100
        print(f"  {tool:20s}: {count:4d} ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
