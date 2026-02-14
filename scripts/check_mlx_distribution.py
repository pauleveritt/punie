"""Check the distribution of tool vs. direct-answer examples in MLX format training data."""

import json
from pathlib import Path

def has_tool_call(text: str) -> bool:
    """Check if text contains a tool call pattern."""
    # Look for tool call patterns in the MLX format
    return (
        "I'll use the" in text
        or "```json" in text and '"name":' in text
        or "Tool result:" in text
    )

def analyze_file(path: Path) -> tuple[int, int]:
    """Analyze a file and return (with_tools, without_tools) counts."""
    with_tools = 0
    without_tools = 0

    with path.open() as f:
        for line in f:
            example = json.loads(line)
            text = example.get("text", "")

            if has_tool_call(text):
                with_tools += 1
            else:
                without_tools += 1

    return with_tools, without_tools

print("=" * 80)
print("MLX Format Training Data Distribution (Phase 5)")
print("=" * 80)

train_path = Path("data/mlx_format/train.jsonl")
valid_path = Path("data/mlx_format/valid.jsonl")

if not train_path.exists() or not valid_path.exists():
    print("❌ Training data not found. Run convert_training_data.py first.")
    exit(1)

# Analyze train set
train_with, train_without = analyze_file(train_path)
train_total = train_with + train_without
train_pct_with = (train_with / train_total * 100) if train_total > 0 else 0
train_pct_without = (train_without / train_total * 100) if train_total > 0 else 0

print(f"\n📊 TRAINING SET ({train_path}):")
print(f"   Total: {train_total}")
print(f"   With tools: {train_with} ({train_pct_with:.1f}%)")
print(f"   Without tools (direct answers): {train_without} ({train_pct_without:.1f}%)")

# Analyze valid set
valid_with, valid_without = analyze_file(valid_path)
valid_total = valid_with + valid_without
valid_pct_with = (valid_with / valid_total * 100) if valid_total > 0 else 0
valid_pct_without = (valid_without / valid_total * 100) if valid_total > 0 else 0

print(f"\n📊 VALIDATION SET ({valid_path}):")
print(f"   Total: {valid_total}")
print(f"   With tools: {valid_with} ({valid_pct_with:.1f}%)")
print(f"   Without tools (direct answers): {valid_without} ({valid_pct_without:.1f}%)")

# Overall statistics
overall_with = train_with + valid_with
overall_without = train_without + valid_without
overall_total = overall_with + overall_without
overall_pct_with = (overall_with / overall_total * 100) if overall_total > 0 else 0
overall_pct_without = (overall_without / overall_total * 100) if overall_total > 0 else 0

print("\n" + "=" * 80)
print(f"📈 OVERALL DISTRIBUTION:")
print(f"   Total examples: {overall_total}")
print(f"   With tools: {overall_with} ({overall_pct_with:.1f}%)")
print(f"   Without tools (direct answers): {overall_without} ({overall_pct_without:.1f}%)")
print("=" * 80)

# Check if we hit the target (75% tool, 25% direct)
target_min = 20
target_max = 30
if target_min <= overall_pct_without <= target_max:
    print(f"✅ Target achieved: {target_min}-{target_max}% direct answers")
else:
    print(f"⚠️  Off target: Need {target_min}-{target_max}% direct answers, got {overall_pct_without:.1f}%")

print(f"\n🎯 Phase 5 Goal: Model should learn to discriminate:")
print(f"   • 'Find all classes...' → use tool (search/read needed)")
print(f"   • 'What is dependency injection?' → direct answer (concept question)")
