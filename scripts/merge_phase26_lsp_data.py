#!/usr/bin/env python
"""Merge training data for Phase 26 LSP navigation.

Combines:
- Phase 22 base (683 examples)
- Phase 23 ty (50 examples)
- Phase 24 ruff/pytest (100 examples)
- Phase 26 field access (120 examples)
- Phase 26 LSP navigation (70 examples)

Total: 1023 examples

Output: data/phase26_lsp_merged/
"""

import json
import shutil
from pathlib import Path


def load_jsonl(file_path: Path) -> list[dict]:
    """Load examples from JSONL file."""
    with file_path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(examples: list[dict], file_path: Path) -> None:
    """Save examples to JSONL file."""
    with file_path.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")


def main():
    """Merge all training data for Phase 26 LSP."""
    # Source directories - use existing phase26_merged as base
    phase26_base_dir = Path("data/phase26_merged")
    phase26_lsp_dir = Path("data/phase26_lsp_navigation")

    # Output directory
    output_dir = Path("data/phase26_lsp_final")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all training data
    print("Loading training data...")

    # Phase 26 base (already includes Phase 22, 23, 24, field access)
    base_train = load_jsonl(phase26_base_dir / "train.jsonl")
    base_valid = load_jsonl(phase26_base_dir / "valid.jsonl")
    base_test = load_jsonl(phase26_base_dir / "test.jsonl")
    base_examples = base_train + base_valid + base_test
    print(f"  Phase 26 base (field access): {len(base_examples)} examples")

    # Phase 26 LSP navigation
    phase26_lsp_examples = load_jsonl(phase26_lsp_dir / "examples.jsonl")
    print(f"  Phase 26 LSP navigation: {len(phase26_lsp_examples)} examples")

    # Merge all examples
    all_examples = base_examples + phase26_lsp_examples

    print(f"\nTotal examples: {len(all_examples)}")

    # Split into train (90%) and valid (10%)
    split_idx = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_idx]
    valid_examples = all_examples[split_idx:]

    print(f"  Train: {len(train_examples)} examples")
    print(f"  Valid: {len(valid_examples)} examples")

    # Save merged data
    print(f"\nSaving to {output_dir}...")
    save_jsonl(train_examples, output_dir / "train.jsonl")
    save_jsonl(valid_examples, output_dir / "valid.jsonl")

    # Create metadata file
    metadata = {
        "total_examples": len(all_examples),
        "train_examples": len(train_examples),
        "valid_examples": len(valid_examples),
        "sources": {
            "phase26_base_field_access": len(base_examples),
            "phase26_lsp_navigation": len(phase26_lsp_examples),
        },
        "description": "Phase 26 LSP + field access merged dataset",
        "note": "phase26_base includes Phase 22 (683), Phase 23 ty (50), Phase 24 ruff/pytest (100), Phase 26 field access (120)",
    }

    with (output_dir / "metadata.json").open("w") as f:
        json.dump(metadata, f, indent=2)

    print("✓ Merge complete")
    print(f"\nOutput:")
    print(f"  {output_dir / 'train.jsonl'}")
    print(f"  {output_dir / 'valid.jsonl'}")
    print(f"  {output_dir / 'metadata.json'}")


if __name__ == "__main__":
    main()
