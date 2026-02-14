#!/usr/bin/env python3
"""Quick script to inspect glaive dataset format."""

from datasets import load_dataset

dataset = load_dataset("glaiveai/glaive-function-calling-v2", split="train")

print("Dataset keys:", dataset.features.keys())
print("\n" + "=" * 80)
print("Sample 1:")
print("=" * 80)
print(dataset[0])

print("\n" + "=" * 80)
print("Sample 2:")
print("=" * 80)
print(dataset[1])

print("\n" + "=" * 80)
print("Sample 3 (different format?):")
print("=" * 80)
print(dataset[100])
