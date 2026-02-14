#!/usr/bin/env python3
"""Debug the JSON extraction."""

import json
import re
from datasets import load_dataset

dataset = load_dataset("glaiveai/glaive-function-calling-v2", split="train")

# Get first example with function call
for item in dataset:
    if '<functioncall>' in item['chat']:
        print("Raw chat content:")
        print("=" * 80)
        print(item['chat'])
        print("=" * 80)

        # Try to extract JSON
        lines = item['chat'].split('\n\n')
        for line in lines:
            if '<functioncall>' in line:
                print(f"\nLine with functioncall:")
                print(repr(line))

                # Extract JSON
                json_start = line.find('<functioncall>') + len('<functioncall>')
                json_str = line[json_start:].strip()

                # Remove <|endoftext|> if present
                json_str = json_str.replace('<|endoftext|>', '').strip()

                print(f"\nExtracted JSON string:")
                print(repr(json_str))

                # Fix: replace single quotes with double quotes
                json_str = json_str.replace("'", '"')

                print(f"\nAfter fixing quotes:")
                print(repr(json_str))

                try:
                    data = json.loads(json_str)
                    print(f"\nParsed successfully!")
                    print(json.dumps(data, indent=2))
                except json.JSONDecodeError as e:
                    print(f"\nJSON parse error: {e}")

        break
