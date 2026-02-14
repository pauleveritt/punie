#!/usr/bin/env python3
"""Debug the parser to see what's happening."""

import sys
sys.path.insert(0, 'scripts')

from convert_public_datasets import parse_glaive_conversation, has_tool_pattern, filter_example
from datasets import load_dataset

dataset = load_dataset("glaiveai/glaive-function-calling-v2", split="train")

# Test with sample 2 (the one with function calls)
print("=" * 80)
print("Testing with sample that HAS function calls:")
print("=" * 80)

item = dataset[1]
full_text = item['system'] + '\n\n' + item['chat']
print("Full text:")
print(full_text[:500])
print("\n")

messages = parse_glaive_conversation(full_text)
print(f"Parsed {len(messages)} messages:")
for i, msg in enumerate(messages):
    print(f"{i}. {msg['role']}: {msg['content'][:100]}...")

print(f"\nHas tool pattern: {has_tool_pattern(messages)}")
print(f"Passes filter: {filter_example(messages)}")

print("\n" + "=" * 80)
print("Looking for examples with function calls...")
print("=" * 80)

tool_examples = 0
for i in range(min(1000, len(dataset))):
    item = dataset[i]
    if '<functioncall>' in item['chat']:
        tool_examples += 1
        if tool_examples <= 3:
            print(f"\nExample {i} has function calls")
            messages = parse_glaive_conversation(item['system'] + '\n\n' + item['chat'])
            if messages:
                print(f"  Parsed: {len(messages)} messages")
                print(f"  Roles: {[m['role'] for m in messages]}")
                print(f"  Has pattern: {has_tool_pattern(messages)}")
                print(f"  Passes filter: {filter_example(messages)}")

print(f"\nFound {tool_examples} examples with function calls in first 1000")
