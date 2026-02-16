#!/usr/bin/env python3
"""Merge Phase 27 cleaned data with Phase 28 targeted examples.

Input:
  data/phase27_cleaned/train.jsonl (938 examples)
  data/phase27_cleaned/valid.jsonl (98 examples)
  data/phase28_targeted/train.jsonl (81 examples)
  data/phase28_targeted/valid.jsonl (9 examples)

Output:
  data/phase28_merged/train.jsonl
  data/phase28_merged/valid.jsonl
"""

import json
import random
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")


def main():
    random.seed(2028)

    # Load all data
    p27_train = load_jsonl(Path("data/phase27_cleaned/train.jsonl"))
    p27_valid = load_jsonl(Path("data/phase27_cleaned/valid.jsonl"))
    p28_train = load_jsonl(Path("data/phase28_targeted/train.jsonl"))
    p28_valid = load_jsonl(Path("data/phase28_targeted/valid.jsonl"))

    print(f"Phase 27 cleaned: {len(p27_train)} train + {len(p27_valid)} valid")
    print(f"Phase 28 targeted: {len(p28_train)} train + {len(p28_valid)} valid")

    # Merge and shuffle
    train = p27_train + p28_train
    valid = p27_valid + p28_valid
    random.shuffle(train)
    random.shuffle(valid)

    print(f"\nMerged: {len(train)} train + {len(valid)} valid = {len(train) + len(valid)} total")

    # Write output
    out_dir = Path("data/phase28_merged")
    write_jsonl(out_dir / "train.jsonl", train)
    write_jsonl(out_dir / "valid.jsonl", valid)

    print(f"Written to {out_dir}/")


if __name__ == "__main__":
    main()
