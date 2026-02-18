#!/usr/bin/env python3
"""Merge Phase 28 merged data with Phase 32 domain tool examples.

Input:
  data/phase28_merged/train.jsonl (1019 examples)
  data/phase28_merged/valid.jsonl (107 examples)
  data/phase32_domain_tools/domain_tool_examples.jsonl (~156 examples)

Output:
  data/phase33_merged/train.jsonl (~1154 examples)
  data/phase33_merged/valid.jsonl (~122 examples)

Total: ~1276 examples (foundation 1126 + domain tools ~150)
"""

import json
import random
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    """Write examples to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")


def split_examples(
    examples: list[dict],
    train_ratio: float = 0.9,
    seed: int = 3201,
) -> tuple[list[dict], list[dict]]:
    """Split examples into train and valid sets."""
    rng = random.Random(seed)
    shuffled = list(examples)
    rng.shuffle(shuffled)
    split = int(len(shuffled) * train_ratio)
    return shuffled[:split], shuffled[split:]


def main() -> None:
    """Merge all data sources into Phase 33 dataset."""
    random.seed(2033)

    # --- Load Phase 28 merged (foundation) ---
    p28_train_path = Path("data/phase28_merged/train.jsonl")
    p28_valid_path = Path("data/phase28_merged/valid.jsonl")

    if not p28_train_path.exists():
        raise FileNotFoundError(f"Foundation data not found: {p28_train_path}")

    p28_train = load_jsonl(p28_train_path)
    p28_valid = load_jsonl(p28_valid_path)
    print(f"Phase 28 merged (foundation): {len(p28_train)} train + {len(p28_valid)} valid")

    # --- Load Phase 32 domain tool examples ---
    p32_path = Path("data/phase32_domain_tools/domain_tool_examples.jsonl")

    if not p32_path.exists():
        raise FileNotFoundError(
            f"Domain tool examples not found: {p32_path}\n"
            "Run: uv run python scripts/generate_phase32_domain_tool_examples.py"
        )

    p32_all = load_jsonl(p32_path)
    print(f"Phase 32 domain tools: {len(p32_all)} examples (before split)")

    # Split Phase 32 examples 90/10
    p32_train, p32_valid = split_examples(p32_all, train_ratio=0.9)
    print(f"Phase 32 split: {len(p32_train)} train + {len(p32_valid)} valid")

    # --- Merge and shuffle ---
    train = p28_train + p32_train
    valid = p28_valid + p32_valid
    random.shuffle(train)
    random.shuffle(valid)

    print("\nMerged totals:")
    print(f"  Train: {len(train)} (foundation {len(p28_train)} + domain {len(p32_train)})")
    print(f"  Valid: {len(valid)} (foundation {len(p28_valid)} + domain {len(p32_valid)})")
    print(f"  Total: {len(train) + len(valid)}")

    # --- Validate all examples ---
    all_examples = train + valid
    malformed = [
        i for i, ex in enumerate(all_examples)
        if "messages" not in ex or len(ex["messages"]) < 2
    ]
    if malformed:
        raise ValueError(f"Found {len(malformed)} malformed examples at indices: {malformed[:5]}")
    print(f"\n✓ All {len(all_examples)} examples have valid {{messages: [...]}} format")

    # --- Category breakdown ---
    print("\nCategory breakdown (from system prompt analysis):")
    categories: dict[str, int] = {}
    for ex in all_examples:
        messages = ex["messages"]
        if len(messages) >= 3:
            assistant_content = messages[2].get("content", "")
            # Detect tool category from assistant response
            if "cst_find_pattern" in assistant_content:
                cat = "cst_find_pattern"
            elif "cst_rename" in assistant_content:
                cat = "cst_rename"
            elif "cst_add_import" in assistant_content:
                cat = "cst_add_import"
            elif "validate_component" in assistant_content:
                cat = "validate_component"
            elif "check_render_tree" in assistant_content:
                cat = "check_render_tree"
            elif "validate_escape_context" in assistant_content:
                cat = "validate_escape_context"
            elif "validate_service_registration" in assistant_content:
                cat = "validate_service_registration"
            elif "check_dependency_graph" in assistant_content:
                cat = "check_dependency_graph"
            elif "validate_injection_site" in assistant_content:
                cat = "validate_injection_site"
            elif "validate_middleware_chain" in assistant_content:
                cat = "validate_middleware_chain"
            elif "check_di_template_binding" in assistant_content:
                cat = "check_di_template_binding"
            elif "validate_route_pattern" in assistant_content:
                cat = "validate_route_pattern"
            else:
                cat = "foundation (phase28)"
        else:
            cat = "unknown"
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # --- Write output ---
    out_dir = Path("data/phase33_merged")
    write_jsonl(out_dir / "train.jsonl", train)
    write_jsonl(out_dir / "valid.jsonl", valid)

    print(f"\nWritten to {out_dir}/")
    print(f"  train.jsonl: {len(train)} examples")
    print(f"  valid.jsonl: {len(valid)} examples")


if __name__ == "__main__":
    main()
