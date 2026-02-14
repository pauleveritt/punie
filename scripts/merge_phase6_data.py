#!/usr/bin/env python3
"""Merge training data for Phase 6 (Python-focused, no HTML yet).

Phase 6 combines:
- Phase 5 examples (244: domain + POC + public)
- Popular repo examples (550+: FastAPI, pytest, etc.)

Total: ~800 examples with balanced tool/direct distribution.
"""

import json
import random
from pathlib import Path


def main():
    print("=" * 80)
    print("PHASE 6 TRAINING DATA MERGER")
    print("=" * 80)
    print("\nCombining training data sources:")
    print("  1. Phase 5 examples (domain-specific)")
    print("  2. Popular repo examples (diverse Python)")
    print()

    all_examples = []

    # Load Phase 5 training data
    phase5_train = Path("data/mlx_format/train.jsonl")
    phase5_valid = Path("data/mlx_format/valid.jsonl")

    if phase5_train.exists():
        print("Loading Phase 5 training data...")
        with phase5_train.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append({
                    "text": item["text"],
                    "source": "phase5_train",
                })

        with phase5_valid.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append({
                    "text": item["text"],
                    "source": "phase5_valid",
                })

        phase5_count = len(all_examples)
        print(f"  ✓ Loaded {phase5_count} Phase 5 examples")
    else:
        print("  ⚠️  Phase 5 data not found, skipping")
        phase5_count = 0

    # Load repo examples
    repos_file = Path("data/repos_examples/training_examples.jsonl")
    if repos_file.exists():
        print("\nLoading repo examples...")
        with repos_file.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append(item)

        repos_count = len(all_examples) - phase5_count
        print(f"  ✓ Loaded {repos_count} repo examples")
    else:
        print("\n  ⚠️  Repo examples not found")
        print("     Run scripts/generate_repo_examples.py first")
        repos_count = 0

    total = len(all_examples)
    print(f"\n{'=' * 80}")
    print(f"TOTAL: {total} examples")
    print(f"  Phase 5: {phase5_count} ({phase5_count/total*100:.1f}%)")
    print(f"  Repos: {repos_count} ({repos_count/total*100:.1f}%)")

    # Analyze distribution
    tool_examples = sum(1 for ex in all_examples if '"name":' in ex["text"])
    direct_examples = total - tool_examples

    print("\nTool vs Direct:")
    print(f"  Tool-calling: {tool_examples} ({tool_examples/total*100:.1f}%)")
    print(f"  Direct: {direct_examples} ({direct_examples/total*100:.1f}%)")

    # Shuffle and split
    print("\nShuffling...")
    random.shuffle(all_examples)

    split_idx = int(len(all_examples) * 0.9)
    train = all_examples[:split_idx]
    valid = all_examples[split_idx:]

    print(f"  Train: {len(train)} (90%)")
    print(f"  Valid: {len(valid)} (10%)")

    # Save
    output_dir = Path("data/phase6_format")
    output_dir.mkdir(parents=True, exist_ok=True)

    train_file = output_dir / "train.jsonl"
    valid_file = output_dir / "valid.jsonl"

    with train_file.open('w') as f:
        for ex in train:
            f.write(json.dumps({"text": ex["text"]}) + '\n')

    with valid_file.open('w') as f:
        for ex in valid:
            f.write(json.dumps({"text": ex["text"]}) + '\n')

    print(f"\n✅ Saved to {output_dir}/")
    print(f"   {train_file.name}: {len(train)} examples")
    print(f"   {valid_file.name}: {len(valid)} examples")
    print()
    print("Next: Train Phase 6 model with:")
    print("  uv run python -m mlx_lm.lora \\")
    print("    --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \\")
    print("    --train --data data/phase6_format \\")
    print("    --iters 500 --batch-size 2 \\")
    print("    --adapter-path adapters_phase6")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)
    main()
