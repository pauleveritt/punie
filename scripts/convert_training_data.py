#!/usr/bin/env python3
"""Convert training data format to MLX-LM multi-turn format.

CRITICAL: Preserves tool-calling traces instead of stripping them.
The old version created simple Query→Answer pairs, which caused the model
to memorize answers instead of learning tool usage patterns.
"""

import json
from pathlib import Path


def format_tool_call(tool_name: str, tool_args: str | dict) -> str:
    """Format a tool call in markdown code fence format.

    Args:
        tool_name: Name of the tool (e.g., "read_file", "run_command")
        tool_args: Tool arguments (string or dict)

    Returns:
        Formatted tool call string
    """
    # Parse args if string
    if isinstance(tool_args, str):
        try:
            args_dict = json.loads(tool_args) if tool_args else {}
        except json.JSONDecodeError:
            args_dict = {}
    else:
        args_dict = tool_args or {}

    # Format as markdown code fence (matches hand-authored examples)
    # Use "name" key to match tool_call_parser.py expectations (line 51)
    tool_json = json.dumps({"name": tool_name, "arguments": args_dict}, indent=2)
    return f"I'll use the {tool_name} tool.\n\n```json\n{tool_json}\n```"


def convert_to_multi_turn_format(example: dict) -> str:
    """Convert training example to multi-turn conversation format.

    Old format (BROKEN - causes memorization):
        User: {query}
        Assistant: {answer}

    New format (CORRECT - teaches tool usage):
        User: {query}
        Assistant: <tool_call>
        User: Tool result: {result}
        Assistant: {answer}

    Args:
        example: Training example dict with query, tool_calls, answer

    Returns:
        Formatted multi-turn conversation string
    """
    tool_calls = example.get("tool_calls", [])
    query = example["query"]
    answer = example["answer"]

    # If no tool calls, create simple conversation
    if not tool_calls:
        return f"""<|im_start|>user
{query}<|im_end|>
<|im_start|>assistant
{answer}<|im_end|>"""

    # Multi-turn conversation with tool calls
    conversation = f"""<|im_start|>system
You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>
<|im_start|>user
{query}<|im_end|>"""

    # Add each tool call and its result (if available)
    for i, tool_call in enumerate(tool_calls):
        # Handle both "name" (correct) and "tool" (legacy) keys for input data
        tool_name = tool_call.get("name", tool_call.get("tool", ""))
        tool_args = tool_call.get("args", {})

        # Format tool call
        tool_call_text = format_tool_call(tool_name, tool_args)
        conversation += f"""
<|im_start|>assistant
{tool_call_text}<|im_end|>"""

        # Add placeholder tool result (since we don't have actual results in current data)
        # TODO: Update generate_training_data.py to capture actual results
        conversation += f"""
<|im_start|>user
Tool result: [Tool execution completed]<|im_end|>"""

    # Add final assistant response
    conversation += f"""
<|im_start|>assistant
{answer}<|im_end|>"""

    return conversation


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

    print("=" * 80)
    print("TRAINING DATA CONVERTER - Multi-Turn Format")
    print("=" * 80)
    print(f"\nConverting {len(examples)} examples...")
    print(f"  Train: {len(train_examples)}")
    print(f"  Valid: {len(valid_examples)}")

    # Count examples with tool calls
    with_tools = len([ex for ex in examples if ex.get("tool_calls")])
    without_tools = len(examples) - with_tools
    print(f"\nTool usage:")
    print(f"  With tools: {with_tools}")
    print(f"  Without tools: {without_tools}")

    # Write train set
    train_file = output_dir / "train.jsonl"
    with train_file.open("w") as f:
        for ex in train_examples:
            text = convert_to_multi_turn_format(ex)
            f.write(json.dumps({"text": text}) + "\n")

    # Write valid set
    valid_file = output_dir / "valid.jsonl"
    with valid_file.open("w") as f:
        for ex in valid_examples:
            text = convert_to_multi_turn_format(ex)
            f.write(json.dumps({"text": text}) + "\n")

    print(f"\n✅ Converted data saved to:")
    print(f"  {train_file}")
    print(f"  {valid_file}")
    print("\n⚠️  Note: Current data uses placeholder tool results.")
    print("   Run generate_training_data.py with updated capture logic for real results.")
    print("=" * 80)


if __name__ == "__main__":
    main()
