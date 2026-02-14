#!/usr/bin/env python3
"""Merge training data for Phase 7 (Python + HTML).

Phase 7 combines:
- Phase 6 data (~800 examples: Python-focused)
- HTML examples (110: HTML structure, forms, semantic HTML)

Total: ~910 examples with Python and HTML domain knowledge.
"""

import json
import random
from pathlib import Path


def main():
    print("=" * 80)
    print("PHASE 7 TRAINING DATA MERGER (Python + HTML)")
    print("=" * 80)
    print("\nCombining training data sources:")
    print("  1. Phase 6 data (Python-focused)")
    print("  2. HTML examples (HTML domain)")
    print()

    all_examples = []

    # Load Phase 6 data
    phase6_train = Path("data/phase6_format/train.jsonl")
    phase6_valid = Path("data/phase6_format/valid.jsonl")

    if phase6_train.exists() and phase6_valid.exists():
        print(f"Loading Phase 6 data...")
        with phase6_train.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append({
                    "text": item["text"],
                    "source": "phase6",
                })

        with phase6_valid.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append({
                    "text": item["text"],
                    "source": "phase6",
                })

        phase6_count = len(all_examples)
        print(f"  ✓ Loaded {phase6_count} Phase 6 examples")
    else:
        print(f"  ⚠️  Phase 6 data not found")
        print(f"     Run scripts/merge_phase6_data.py first")
        phase6_count = 0

    # Load HTML examples
    html_file = Path("data/html_examples/training_examples.jsonl")
    if html_file.exists():
        print(f"\nLoading HTML examples...")
        with html_file.open() as f:
            for line in f:
                item = json.loads(line)
                all_examples.append(item)

        html_count = len(all_examples) - phase6_count
        print(f"  ✓ Loaded {html_count} HTML examples")
    else:
        print(f"\n  ⚠️  HTML examples not found")
        print(f"     Run scripts/generate_html_examples.py first")
        html_count = 0

    total = len(all_examples)
    print(f"\n{'=' * 80}")
    print(f"TOTAL: {total} examples")
    print(f"  Phase 6 (Python): {phase6_count} ({phase6_count/total*100:.1f}%)")
    print(f"  HTML: {html_count} ({html_count/total*100:.1f}%)")

    # Analyze distribution
    tool_examples = sum(1 for ex in all_examples if '"name":' in ex["text"])
    direct_examples = total - tool_examples

    print(f"\nTool vs Direct:")
    print(f"  Tool-calling: {tool_examples} ({tool_examples/total*100:.1f}%)")
    print(f"  Direct: {direct_examples} ({direct_examples/total*100:.1f}%)")

    # Shuffle and split
    print(f"\nShuffling...")
    random.shuffle(all_examples)

    split_idx = int(len(all_examples) * 0.9)
    train = all_examples[:split_idx]
    valid = all_examples[split_idx:]

    print(f"  Train: {len(train)} (90%)")
    print(f"  Valid: {len(valid)} (10%)")

    # Save
    output_dir = Path("data/phase7_format")
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
    print("Next: Train Phase 7 model with:")
    print("  uv run python -m mlx_lm.lora \\")
    print("    --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \\")
    print("    --train --data data/phase7_format \\")
    print("    --iters 500 --batch-size 2 \\")
    print("    --adapter-path adapters_phase7")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)
    main()
