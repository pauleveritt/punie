#!/usr/bin/env python3
"""Debug the convert_to_qwen_format function."""

import sys
sys.path.insert(0, 'scripts')

from convert_public_datasets import parse_glaive_conversation, has_tool_pattern, filter_example, convert_to_qwen_format
from datasets import load_dataset

dataset = load_dataset("glaiveai/glaive-function-calling-v2", split="train")

print("Testing first 100 examples with function calls...\n")

checked = 0
passed_convert = 0
failed_convert = 0

for item in dataset:
    if '<functioncall>' not in item['chat']:
        continue

    checked += 1

    # Parse
    messages = parse_glaive_conversation(item['system'] + '\n\n' + item['chat'])
    if not messages:
        continue

    # Check pattern and filter
    if not has_tool_pattern(messages) or not filter_example(messages):
        continue

    # Try to convert
    qwen_text = convert_to_qwen_format(messages)
    if qwen_text:
        passed_convert += 1
        if passed_convert <= 3:
            print(f"Example {checked} PASSED conversion:")
            print(qwen_text[:300])
            print("...\n")
    else:
        failed_convert += 1
        if failed_convert <= 5:
            print(f"Example {checked} FAILED conversion:")
            print(f"  Messages: {len(messages)}")
            for i, m in enumerate(messages):
                content_preview = m['content'][:80].replace('\n', ' ')
                print(f"    {i}. {m['role']}: {content_preview}...")
            print()

    if checked >= 100:
        break

print(f"\nResults:")
print(f"  Passed conversion: {passed_convert}")
print(f"  Failed conversion: {failed_convert}")
