#!/usr/bin/env python3
"""Check distribution of function calls in dataset."""

from datasets import load_dataset

dataset = load_dataset("glaiveai/glaive-function-calling-v2", split="train")

print(f"Total examples: {len(dataset)}")

# Count examples with function calls
with_tools = 0
without_tools = 0

for i, item in enumerate(dataset):
    if '<functioncall>' in item['chat']:
        with_tools += 1
    else:
        without_tools += 1

    if (i + 1) % 10000 == 0:
        print(f"Processed {i + 1} examples: {with_tools} with tools, {without_tools} without")

print(f"\nFinal: {with_tools} with function calls, {without_tools} without")
print(f"Percentage with tools: {with_tools / len(dataset) * 100:.1f}%")
