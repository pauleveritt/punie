"""Check the distribution of tool vs. direct-answer examples in Phase 5 training data."""

import json
from pathlib import Path

# Count examples in each source
sources = {
    "domain": Path("data/domain_examples.jsonl"),
    "poc": Path("data/training_examples_punie_poc.jsonl"),
    "public": Path("data/public_dataset_converted.jsonl"),
}

def has_tool_call(example: dict) -> bool:
    """Check if an example contains a tool call."""
    messages = example.get("messages", [])
    for msg in messages:
        content = msg.get("content", "")
        # Check for tool call patterns
        if "```json" in content and '"name":' in content and '"arguments":' in content:
            return True
        if "Tool result:" in content:
            return True
    return False

print("=" * 80)
print("Phase 5 Training Data Distribution")
print("=" * 80)

total_with_tools = 0
total_without_tools = 0

for name, path in sources.items():
    if not path.exists():
        print(f"\n❌ {name}: File not found - {path}")
        continue

    with_tools = 0
    without_tools = 0

    with path.open() as f:
        for line in f:
            example = json.loads(line)
            if has_tool_call(example):
                with_tools += 1
            else:
                without_tools += 1

    total_with_tools += with_tools
    total_without_tools += without_tools

    total = with_tools + without_tools
    pct_with = (with_tools / total * 100) if total > 0 else 0
    pct_without = (without_tools / total * 100) if total > 0 else 0

    print(f"\n📊 {name.upper()}:")
    print(f"   Total: {total}")
    print(f"   With tools: {with_tools} ({pct_with:.1f}%)")
    print(f"   Without tools: {without_tools} ({pct_without:.1f}%)")

# Overall statistics
print("\n" + "=" * 80)
total = total_with_tools + total_without_tools
pct_with = (total_with_tools / total * 100) if total > 0 else 0
pct_without = (total_without_tools / total * 100) if total > 0 else 0

print("📈 OVERALL DISTRIBUTION:")
print(f"   Total examples: {total}")
print(f"   With tools: {total_with_tools} ({pct_with:.1f}%)")
print(f"   Without tools: {total_without_tools} ({pct_without:.1f}%)")
print("=" * 80)

# Check if we hit the target
if 20 <= pct_without <= 30:
    print("✅ Target achieved: 20-30% direct answers")
else:
    print(f"⚠️  Off target: Need 20-30% direct answers, got {pct_without:.1f}%")
