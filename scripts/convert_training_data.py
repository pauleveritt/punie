#!/usr/bin/env python3
"""Convert our training data format to MLX-LM format."""

import json
from pathlib import Path

def convert_to_mlx_format(input_file: Path, output_file: Path):
    """Convert custom training format to MLX-LM instruction format.

    MLX-LM expects: {"text": "formatted prompt + completion"}
    """
    with input_file.open("r") as f_in, output_file.open("w") as f_out:
        for line in f_in:
            example = json.loads(line)

            # Format as instruction-following conversation
            # Using Qwen's chat format
            text = f"""<|im_start|>user
{example['query']}<|im_end|>
<|im_start|>assistant
{example['answer']}<|im_end|>"""

            mlx_example = {"text": text}
            f_out.write(json.dumps(mlx_example) + "\n")

def main():
    input_file = Path("data/training_examples_1k.jsonl")
    output_dir = Path("data/mlx_format")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert and split into train/valid sets (90/10 split)
    examples = []
    with input_file.open("r") as f:
        for line in f:
            examples.append(json.loads(line))

    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

    print(f"Converting {len(examples)} examples...")
    print(f"  Train: {len(train_examples)}")
    print(f"  Valid: {len(valid_examples)}")

    # Write train set
    train_file = output_dir / "train.jsonl"
    with train_file.open("w") as f:
        for ex in train_examples:
            text = f"""<|im_start|>user
{ex['query']}<|im_end|>
<|im_start|>assistant
{ex['answer']}<|im_end|>"""
            f.write(json.dumps({"text": text}) + "\n")

    # Write valid set
    valid_file = output_dir / "valid.jsonl"
    with valid_file.open("w") as f:
        for ex in valid_examples:
            text = f"""<|im_start|>user
{ex['query']}<|im_end|>
<|im_start|>assistant
{ex['answer']}<|im_end|>"""
            f.write(json.dumps({"text": text}) + "\n")

    print(f"\n✅ Converted data saved to:")
    print(f"  {train_file}")
    print(f"  {valid_file}")

if __name__ == "__main__":
    main()
