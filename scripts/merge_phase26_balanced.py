#!/usr/bin/env python
"""Merge LSP and non-LSP examples into balanced Phase 26 dataset.

Sources:
- data/phase26_lsp_expanded/examples.jsonl (400 LSP examples)
- data/phase26_curated_non_lsp/examples.jsonl (400 non-LSP examples)

Output: data/phase26_balanced/ with 800 examples (50/50 split)
"""

import json
import random
from pathlib import Path


def load_jsonl(file_path: Path) -> list[dict]:
    """Load examples from JSONL file."""
    examples = []
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


def main():
    """Merge LSP and non-LSP examples."""
    print("Merging balanced Phase 26 dataset...")

    # Load LSP examples
    print("\n1. Loading LSP examples...")
    lsp_examples = load_jsonl(Path("data/phase26_lsp_expanded/examples.jsonl"))
    print(f"   Found {len(lsp_examples)} LSP examples")

    # Load non-LSP examples
    print("\n2. Loading non-LSP examples...")
    non_lsp_examples = load_jsonl(Path("data/phase26_curated_non_lsp/examples.jsonl"))
    print(f"   Found {len(non_lsp_examples)} non-LSP examples")

    # Combine and shuffle
    print("\n3. Combining and shuffling...")
    all_examples = lsp_examples + non_lsp_examples
    random.seed(42)  # For reproducibility
    random.shuffle(all_examples)
    print(f"   Total: {len(all_examples)} examples")

    # Split 90/10 train/valid
    split_point = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_point]
    valid_examples = all_examples[split_point:]

    print(f"\n4. Splitting train/valid (90/10)...")
    print(f"   Train: {len(train_examples)} examples")
    print(f"   Valid: {len(valid_examples)} examples")

    # Save
    output_dir = Path("data/phase26_balanced")
    save_jsonl(train_examples, output_dir / "train.jsonl")
    save_jsonl(valid_examples, output_dir / "valid.jsonl")

    # Save metadata
    metadata = {
        "total_examples": len(all_examples),
        "train_examples": len(train_examples),
        "valid_examples": len(valid_examples),
        "lsp_examples": len(lsp_examples),
        "non_lsp_examples": len(non_lsp_examples),
        "balance": "50% LSP, 50% non-LSP",
        "sources": [
            "data/phase26_lsp_expanded/examples.jsonl",
            "data/phase26_curated_non_lsp/examples.jsonl",
        ],
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Saved to {output_dir}/")
    print(f"  - train.jsonl ({len(train_examples)} examples)")
    print(f"  - valid.jsonl ({len(valid_examples)} examples)")
    print(f"  - metadata.json")

    # Statistics
    print(f"\nDataset composition:")
    print(f"  Total: {len(all_examples)}")
    print(f"  LSP: {len(lsp_examples)} (50.0%)")
    print(f"  Non-LSP: {len(non_lsp_examples)} (50.0%)")
    print(f"\nSplit:")
    print(f"  Train: {len(train_examples)} (90%)")
    print(f"  Valid: {len(valid_examples)} (10%)")


if __name__ == "__main__":
    main()
