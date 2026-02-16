"""Merge Phase 27 training data with Phase 26 balanced data.

Sources:
- Phase 26 balanced (non-LSP): 400 examples (from data/phase26_curated_non_lsp)
- Phase 26 balanced (LSP): 400 examples (from data/phase26_contrastive)
- Phase 27 new LSP: 84 examples
- Phase 27 git: 84 examples
- Phase 27 rebalance: 96 examples
- Phase 27 direct answers: 40 examples

Total: ~1104 examples → 90/10 split → ~994 train / ~110 valid
"""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(46)


def load_jsonl(file_path: Path) -> list[dict]:
    """Load examples from a JSONL file."""
    examples = []
    if file_path.exists():
        with open(file_path) as f:
            for line in f:
                examples.append(json.loads(line))
    return examples


def main():
    """Merge all Phase 27 data sources."""
    # Create output directory
    output_dir = Path("data/phase27_merged")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_examples = []

    # Load Phase 26 balanced data (800 examples)
    print("Loading Phase 26 balanced data...")
    phase26_train = Path("data/phase26_balanced/train.jsonl")
    phase26_valid = Path("data/phase26_balanced/valid.jsonl")

    if phase26_train.exists():
        phase26_train_data = load_jsonl(phase26_train)
        all_examples.extend(phase26_train_data)
        print(f"  Loaded {len(phase26_train_data)} train examples")
    if phase26_valid.exists():
        phase26_valid_data = load_jsonl(phase26_valid)
        all_examples.extend(phase26_valid_data)
        print(f"  Loaded {len(phase26_valid_data)} valid examples")

    # Load Phase 27 new examples
    print("\nLoading Phase 27 new examples...")

    phase27_lsp = Path("data/phase27_lsp/phase27_lsp_examples.jsonl")
    if phase27_lsp.exists():
        lsp_examples = load_jsonl(phase27_lsp)
        all_examples.extend(lsp_examples)
        print(f"  Loaded {len(lsp_examples)} LSP examples")

    phase27_git = Path("data/phase27_git/phase27_git_examples.jsonl")
    if phase27_git.exists():
        git_examples = load_jsonl(phase27_git)
        all_examples.extend(git_examples)
        print(f"  Loaded {len(git_examples)} git examples")

    phase27_rebalance = Path("data/phase27_rebalance/phase27_rebalance_examples.jsonl")
    if phase27_rebalance.exists():
        rebalance_examples = load_jsonl(phase27_rebalance)
        all_examples.extend(rebalance_examples)
        print(f"  Loaded {len(rebalance_examples)} rebalance examples")

    phase27_direct = Path("data/phase27_direct_answers/phase27_direct_answers.jsonl")
    if phase27_direct.exists():
        direct_examples = load_jsonl(phase27_direct)
        all_examples.extend(direct_examples)
        print(f"  Loaded {len(direct_examples)} direct-answer examples")

    print(f"\n{'='*60}")
    print(f"Total examples loaded: {len(all_examples)}")
    print(f"{'='*60}")

    # Shuffle all examples
    print("\nShuffling examples...")
    random.shuffle(all_examples)

    # Split 90/10
    split_index = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_index]
    valid_examples = all_examples[split_index:]

    print(f"\nSplit:")
    print(f"  Train: {len(train_examples)} examples ({len(train_examples)/len(all_examples)*100:.1f}%)")
    print(f"  Valid: {len(valid_examples)} examples ({len(valid_examples)/len(all_examples)*100:.1f}%)")

    # Save train split
    train_file = output_dir / "train.jsonl"
    with open(train_file, "w") as f:
        for example in train_examples:
            f.write(json.dumps(example) + "\n")
    print(f"\nSaved train data to: {train_file}")

    # Save valid split
    valid_file = output_dir / "valid.jsonl"
    with open(valid_file, "w") as f:
        for example in valid_examples:
            f.write(json.dumps(example) + "\n")
    print(f"Saved valid data to: {valid_file}")

    print(f"\n{'='*60}")
    print("Phase 27 data merge complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
