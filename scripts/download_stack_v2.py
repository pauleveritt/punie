#!/usr/bin/env python3
"""Download and filter The Stack v2 Python dataset for quality examples.

The Stack v2 is ethically sourced (MIT/Apache/BSD licenses only) and contains
400GB of Python code. We filter for:
- High-quality code (minimal syntax errors)
- Diverse projects (web, data, testing, CLI, etc.)
- Well-structured files (classes, functions, docstrings)
- Reasonable file size (100-2000 lines)

This provides a corpus for generating tool-calling training examples.
"""

import json
import random
from pathlib import Path
from typing import Iterator

from datasets import load_dataset

# Quality filters
MIN_FILE_SIZE = 100  # Minimum 100 characters
MAX_FILE_SIZE = 50000  # Maximum ~50KB per file
MIN_LINES = 10  # Minimum 10 lines
MAX_LINES = 2000  # Maximum 2000 lines

# Diversity keywords (ensure we get different types of projects)
DIVERSITY_KEYWORDS = {
    "web": ["flask", "django", "fastapi", "starlette", "tornado", "bottle"],
    "data": ["pandas", "numpy", "scipy", "sklearn", "tensorflow", "pytorch"],
    "testing": ["pytest", "unittest", "mock", "fixture", "parametrize"],
    "cli": ["argparse", "click", "typer", "fire", "docopt"],
    "async": ["asyncio", "aiohttp", "trio", "anyio"],
    "typing": ["Protocol", "TypeVar", "Generic", "Callable", "Union"],
    "tools": ["setuptools", "poetry", "flit", "build", "wheel"],
}


def estimate_quality(code: str) -> float:
    """Estimate code quality on 0-1 scale based on heuristics.

    Higher scores for:
    - Has docstrings
    - Has type hints
    - Has classes/functions
    - Proper indentation
    - Not too many TODOs/FIXMEs
    """
    score = 0.0
    lines = code.split('\n')

    # Has docstrings
    if '"""' in code or "'''" in code:
        score += 0.2

    # Has type hints
    if '->' in code or ': ' in code:
        score += 0.2

    # Has classes or functions
    if 'class ' in code:
        score += 0.2
    if 'def ' in code:
        score += 0.2

    # Not too many TODOs
    todo_count = code.lower().count('todo') + code.lower().count('fixme')
    if todo_count == 0:
        score += 0.1
    elif todo_count <= 2:
        score += 0.05

    # Reasonable comment ratio (5-30%)
    comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
    comment_ratio = comment_lines / max(len(lines), 1)
    if 0.05 <= comment_ratio <= 0.30:
        score += 0.1

    return score


def get_diversity_category(code: str) -> str | None:
    """Identify which diversity category this code belongs to."""
    code_lower = code.lower()
    for category, keywords in DIVERSITY_KEYWORDS.items():
        if any(keyword in code_lower for keyword in keywords):
            return category
    return None


def filter_code(item: dict) -> dict | None:
    """Filter a code item for quality and extract metadata.

    Returns dict with code and metadata, or None if filtered out.
    """
    content = item.get("content", "")

    # Size filters
    if len(content) < MIN_FILE_SIZE or len(content) > MAX_FILE_SIZE:
        return None

    lines = content.split('\n')
    if len(lines) < MIN_LINES or len(lines) > MAX_LINES:
        return None

    # Must be valid Python (at least has some Python keywords)
    python_keywords = ["def ", "class ", "import ", "from "]
    if not any(keyword in content for keyword in python_keywords):
        return None

    # Estimate quality
    quality = estimate_quality(content)
    if quality < 0.3:  # Threshold: at least 0.3/1.0
        return None

    # Get diversity category
    category = get_diversity_category(content)

    return {
        "content": content,
        "quality": quality,
        "category": category,
        "lines": len(lines),
        "size": len(content),
        "path": item.get("path", "unknown"),
    }


def sample_diverse(items: list[dict], target_count: int = 500) -> list[dict]:
    """Sample items ensuring diversity across categories.

    Tries to get equal representation from each category.
    """
    # Group by category
    by_category = {}
    for item in items:
        category = item["category"] or "other"
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(item)

    # Calculate samples per category
    num_categories = len(by_category)
    per_category = target_count // num_categories

    print(f"\nCategory distribution (before sampling):")
    for category, items in sorted(by_category.items()):
        print(f"  {category}: {len(items)} files")

    # Sample from each category
    sampled = []
    for category, cat_items in by_category.items():
        # Sort by quality and take top items
        cat_items.sort(key=lambda x: x["quality"], reverse=True)
        sample_size = min(per_category, len(cat_items))
        sampled.extend(cat_items[:sample_size])

    # If we're short, add more from largest categories
    remaining = target_count - len(sampled)
    if remaining > 0:
        # Get categories sorted by size
        sorted_cats = sorted(by_category.items(),
                           key=lambda x: len(x[1]),
                           reverse=True)
        for category, cat_items in sorted_cats:
            if remaining <= 0:
                break
            # Add items not already sampled
            available = [item for item in cat_items if item not in sampled]
            add_count = min(remaining, len(available))
            sampled.extend(available[:add_count])
            remaining -= add_count

    # Shuffle and return
    random.shuffle(sampled)
    return sampled[:target_count]


def main():
    print("=" * 80)
    print("THE STACK V2 PYTHON DATASET DOWNLOADER")
    print("=" * 80)
    print("\nThis will download and filter Python code from The Stack v2")
    print("(ethically sourced with MIT/Apache/BSD licenses only)")
    print()

    # Create output directory
    output_dir = Path("data/stack_v2")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading The Stack v2 Python dataset...")
    print("(This may take several minutes on first run)")
    print()

    # Load dataset in streaming mode (doesn't download everything at once)
    dataset = load_dataset(
        "bigcode/the-stack-v2",
        data_dir="data/python",
        split="train",
        streaming=True,
    )

    print("✓ Dataset loaded in streaming mode\n")
    print("Filtering for high-quality, diverse Python files...")
    print(f"  Quality threshold: 0.3/1.0")
    print(f"  Size range: {MIN_FILE_SIZE}-{MAX_FILE_SIZE} chars")
    print(f"  Line range: {MIN_LINES}-{MAX_LINES} lines")
    print()

    # Process items with progress
    filtered_items = []
    processed = 0
    filtered_out = 0
    target = 5000  # Process enough to get 500 good ones

    print(f"Processing up to {target} files...")
    for item in dataset:
        processed += 1

        if processed % 100 == 0:
            print(f"  Processed: {processed}, Filtered: {len(filtered_items)}, "
                  f"Rejected: {filtered_out}")

        # Filter
        filtered = filter_code(item)
        if filtered:
            filtered_items.append(filtered)
        else:
            filtered_out += 1

        # Stop when we have enough
        if len(filtered_items) >= target:
            break

        # Safety limit
        if processed >= target * 3:
            print(f"\n⚠️  Reached safety limit ({target * 3} files processed)")
            break

    print(f"\n✓ Filtering complete!")
    print(f"  Processed: {processed}")
    print(f"  Passed filters: {len(filtered_items)}")
    print(f"  Rejected: {filtered_out}")
    print(f"  Pass rate: {len(filtered_items) / processed * 100:.1f}%")

    # Sample for diversity
    print(f"\nSampling for diversity (target: 500 files)...")
    sampled = sample_diverse(filtered_items, target_count=500)

    print(f"\n✓ Sampled {len(sampled)} diverse files")

    # Show final distribution
    category_counts = {}
    for item in sampled:
        cat = item["category"] or "other"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print(f"\nFinal category distribution:")
    for category in sorted(category_counts.keys()):
        count = category_counts[category]
        print(f"  {category}: {count} files ({count/len(sampled)*100:.1f}%)")

    # Show quality distribution
    qualities = [item["quality"] for item in sampled]
    avg_quality = sum(qualities) / len(qualities)
    print(f"\nQuality statistics:")
    print(f"  Average: {avg_quality:.2f}")
    print(f"  Min: {min(qualities):.2f}")
    print(f"  Max: {max(qualities):.2f}")

    # Save to JSONL
    output_file = output_dir / "filtered_python.jsonl"
    with output_file.open('w') as f:
        for item in sampled:
            f.write(json.dumps(item) + '\n')

    print(f"\n✅ Saved to {output_file}")
    print(f"   {len(sampled)} files ready for example generation")
    print()
    print("Next step: Run scripts/generate_stack_examples.py")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)  # Reproducible sampling
    main()
