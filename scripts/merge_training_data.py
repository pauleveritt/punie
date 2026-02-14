#!/usr/bin/env python3
"""Merge all training data sources for Phase 6 training.

Combines:
1. Existing Phase 5 examples (244 examples: POC + domain + public)
2. New Stack v2 examples (550+ examples: diverse Python codebases)

Total: ~800 examples with good tool/direct balance.
"""

import json
import random
from pathlib import Path


def main():
    print("=" * 80)
    print("TRAINING DATA MERGER - Phase 6")
    print("=" * 80)
    print("\nCombining all training data sources:")
    print("  1. Phase 5 examples (domain + POC + public)")
    print("  2. Popular repo examples (FastAPI, pytest, etc.)")
    print()

    all_examples = []

    # Load existing Phase 5 training data
    phase5_train = Path("data/mlx_format/train.jsonl")
    phase5_valid = Path("data/mlx_format/valid.jsonl")

    if phase5_train.exists():
        print(f"Loading Phase 5 training data from {phase5_train}...")
        with phase5_train.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append({
                    "text": item["text"],
                    "source": "phase5_train",
                })

        print(f"  Loaded {len([ex for ex in all_examples if ex['source'] == 'phase5_train'])} examples")

    if phase5_valid.exists():
        print(f"Loading Phase 5 validation data from {phase5_valid}...")
        with phase5_valid.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append({
                    "text": item["text"],
                    "source": "phase5_valid",
                })

        print(f"  Loaded {len([ex for ex in all_examples if ex['source'] == 'phase5_valid'])} examples")

    phase5_count = len(all_examples)

    # Load repo examples (from popular Python projects)
    repos_file = Path("data/repos_examples/training_examples.jsonl")
    if repos_file.exists():
        print(f"\nLoading repo examples from {repos_file}...")
        with repos_file.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append(item)

        repos_count = len(all_examples) - phase5_count
        print(f"  Loaded {repos_count} examples")
    else:
        print(f"\n⚠️  Warning: {repos_file} not found")
        print("   Run scripts/generate_repo_examples.py first")
        repos_count = 0

    total = len(all_examples)
    print(f"\n✓ Total examples: {total}")
    print(f"  Phase 5: {phase5_count} ({phase5_count/total*100:.1f}%)")
    print(f"  Repos: {repos_count} ({repos_count/total*100:.1f}%)")

    # Analyze tool vs direct distribution
    tool_examples = sum(1 for ex in all_examples if '"name":' in ex["text"])
    direct_examples = total - tool_examples

    print(f"\nTool vs Direct distribution:")
    print(f"  Tool-calling: {tool_examples} ({tool_examples/total*100:.1f}%)")
    print(f"  Direct answers: {direct_examples} ({direct_examples/total*100:.1f}%)")

    # Shuffle
    print(f"\nShuffling examples...")
    random.shuffle(all_examples)

    # Split 90/10 for train/valid
    split_idx = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_idx]
    valid_examples = all_examples[split_idx:]

    print(f"  Train: {len(train_examples)}")
    print(f"  Valid: {len(valid_examples)}")

    # Save to Phase 6 directory
    output_dir = Path("data/phase6_format")
    output_dir.mkdir(parents=True, exist_ok=True)

    train_file = output_dir / "train.jsonl"
    valid_file = output_dir / "valid.jsonl"

    print(f"\nSaving to {output_dir}/...")
    with train_file.open('w') as f:
        for ex in train_examples:
            f.write(json.dumps({"text": ex["text"]}) + '\n')

    with valid_file.open('w') as f:
        for ex in valid_examples:
            f.write(json.dumps({"text": ex["text"]}) + '\n')

    print(f"✓ Saved {len(train_examples)} training examples to {train_file}")
    print(f"✓ Saved {len(valid_examples)} validation examples to {valid_file}")

    print(f"\n✅ Phase 6 training data ready!")
    print(f"   Total: {total} examples ({tool_examples} tool, {direct_examples} direct)")
    print(f"   Train/Valid split: 90/10")
    print()
    print("Next step: Train Phase 6 model with:")
    print(f"  uv run python -m mlx_lm.lora \\")
    print(f"    --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \\")
    print(f"    --train --data data/phase6_format \\")
    print(f"    --iters 500 --batch-size 2 --learning-rate 1e-4 \\")
    print(f"    --num-layers 16 --adapter-path adapters_phase6 \\")
    print(f"    --save-every 250 --val-batches 10 --test")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)
    main()
