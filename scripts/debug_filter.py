#!/usr/bin/env python3
"""Debug why so many examples are filtered out."""

import sys
sys.path.insert(0, 'scripts')

from convert_public_datasets import parse_glaive_conversation, has_tool_pattern
from datasets import load_dataset

dataset = load_dataset("glaiveai/glaive-function-calling-v2", split="train")

print("Testing first 100 examples with function calls...\n")

# Test with samples that have function calls
checked = 0
passed_parse = 0
passed_pattern = 0
passed_filter = 0
failed_reasons = {
    'parse': 0,
    'pattern': 0,
    'length': 0,
    'structure': 0,
}

for item in dataset:
    if '<functioncall>' not in item['chat']:
        continue

    checked += 1

    # Parse
    messages = parse_glaive_conversation(item['system'] + '\n\n' + item['chat'])
    if not messages:
        failed_reasons['parse'] += 1
        continue

    passed_parse += 1

    # Check pattern
    if not has_tool_pattern(messages):
        failed_reasons['pattern'] += 1
        if checked <= 5:
            print(f"Example {checked} FAILED pattern check:")
            print(f"  Roles: {[m['role'] for m in messages]}")
            has_functioncall = [('<functioncall>' in m['content']) for m in messages if m['role'] == 'ASSISTANT']
            print(f"  Has <functioncall>: {any(has_functioncall)}")
            print()
        continue

    passed_pattern += 1

    # Check filter
    text_length = sum(len(m['content']) for m in messages)
    roles = [m['role'] for m in messages]

    if text_length > 2048 * 4:
        failed_reasons['length'] += 1
        continue

    if 'SYSTEM' not in roles or 'USER' not in roles or 'ASSISTANT' not in roles:
        failed_reasons['structure'] += 1
        continue

    passed_filter += 1

    if checked >= 100:
        break

print(f"\nResults from {checked} examples with <functioncall>:")
print(f"  Passed parse: {passed_parse} ({passed_parse/checked*100:.1f}%)")
print(f"  Passed pattern check: {passed_pattern} ({passed_pattern/checked*100:.1f}%)")
print(f"  Passed filter: {passed_filter} ({passed_filter/checked*100:.1f}%)")
print("\nFailure reasons:")
for reason, count in failed_reasons.items():
    if count > 0:
        print(f"  {reason}: {count} ({count/checked*100:.1f}%)")
