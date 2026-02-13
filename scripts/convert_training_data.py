#!/usr/bin/env python3
"""Convert training data to MLX-LM format - Phase 2 Recovery.

Phase 1 showed the model CAN learn to call tools with {text} format + Qwen tokens.
The infinite loop was caused by placeholder tool results.

Recovery strategy:
- Use ONLY generated examples WITHOUT tool calls (15 simple Q&A pairs)
- Keep the {text} format with Qwen tokens that worked in Phase 1
- Skip hand-authored examples (wrong format - teach markdown generation not API calls)
- Next: Fix generator to capture real results, then retrain with those

This minimal dataset prevents regression while we fix the generator (Step 2).
"""

import json
import random
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

    # Format as markdown code fence
    tool_json = json.dumps({"name": tool_name, "arguments": args_dict}, indent=2)
    return f"I'll use the {tool_name} tool.\n\n```json\n{tool_json}\n```"


def convert_to_qwen_format(example: dict) -> str:
    """Convert example to Qwen chat format with tool calls.

    Args:
        example: Dict with "query", "answer", and optional "tool_calls" fields

    Returns:
        Formatted conversation string with Qwen tokens
    """
    tool_calls = example.get("tool_calls", [])
    query = example["query"]
    answer = example["answer"]

    # If no tool calls, create simple conversation
    if not tool_calls:
        return f"""<|im_start|>system
You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>
<|im_start|>user
{query}<|im_end|>
<|im_start|>assistant
{answer}<|im_end|>"""

    # Multi-turn conversation with tool calls
    conversation = f"""<|im_start|>system
You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>
<|im_start|>user
{query}<|im_end|>"""

    # Add each tool call and its result
    for tool_call in tool_calls:
        # Handle both "name" (correct) and "tool" (legacy) keys
        tool_name = tool_call.get("name", tool_call.get("tool", ""))
        tool_args = tool_call.get("args", {})
        tool_result = tool_call.get("result")

        # Format tool call
        tool_call_text = format_tool_call(tool_name, tool_args)
        conversation += f"""
<|im_start|>assistant
{tool_call_text}<|im_end|>"""

        # Add real tool result (not placeholder!)
        if tool_result is not None:
            conversation += f"""
<|im_start|>user
Tool result: {tool_result}<|im_end|>"""
        else:
            # Skip examples with missing results
            return None

    # Add final assistant response
    conversation += f"""
<|im_start|>assistant
{answer}<|im_end|>"""

    return conversation


def main():
    input_file = Path("data/training_examples_1k.jsonl")
    output_dir = Path("data/mlx_format")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TRAINING DATA CONVERTER - Phase 2B: Real Tool Results")
    print("=" * 80)

    # Load generated examples - include tool examples WITH real results
    examples = []
    with_tools_no_results = 0
    with_tools_with_results = 0
    without_tools = 0

    with input_file.open("r") as f:
        for line in f:
            example = json.loads(line)
            tool_calls = example.get("tool_calls", [])

            if not tool_calls:
                # Simple Q&A without tools
                examples.append(example)
                without_tools += 1
            else:
                # Check if ALL tool calls have real results (not None)
                has_all_results = all(tc.get("result") is not None for tc in tool_calls)
                if has_all_results:
                    examples.append(example)
                    with_tools_with_results += 1
                else:
                    # Skip examples with placeholder/missing results
                    with_tools_no_results += 1

    print(f"\n✓ Loaded examples:")
    print(f"  Without tools: {without_tools}")
    print(f"  With tools + real results: {with_tools_with_results}")
    print(f"  With tools + NO results: {with_tools_no_results} (skipped)")
    print(f"  Total included: {len(examples)}")
    print("\n⚠️  Skipping hand-authored examples (wrong format)")
    print("   They use markdown tool calls, not function calling API")

    # Shuffle
    random.seed(42)
    random.shuffle(examples)

    # Split 90/10
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

    print(f"\n✓ Split:")
    print(f"  Train: {len(train_examples)} examples")
    print(f"  Valid: {len(valid_examples)} examples")

    # Write train set
    train_file = output_dir / "train.jsonl"
    train_written = 0
    with train_file.open("w") as f:
        for ex in train_examples:
            text = convert_to_qwen_format(ex)
            if text is not None:
                f.write(json.dumps({"text": text}) + "\n")
                train_written += 1

    # Write valid set
    valid_file = output_dir / "valid.jsonl"
    valid_written = 0
    with valid_file.open("w") as f:
        for ex in valid_examples:
            text = convert_to_qwen_format(ex)
            if text is not None:
                f.write(json.dumps({"text": text}) + "\n")
                valid_written += 1

    print(f"\n✅ Converted data saved to:")
    print(f"  {train_file} ({train_written} examples)")
    print(f"  {valid_file} ({valid_written} examples)")
    print("\n📝 Format: {{text: ...}} with Qwen chat tokens")
    print("   This format worked in Phase 1 for teaching tool calling")
    if with_tools_with_results > 0:
        print(f"\n✅ Includes {with_tools_with_results} examples with REAL tool results!")
        print("   Model will learn when to stop calling tools and give final answer")
    else:
        print("\n⚠️  No examples with real tool results yet")
        print("   Run: uv run python scripts/generate_training_data.py")
        print("   This will capture real results using the fixed generator")
    print("=" * 80)


if __name__ == "__main__":
    main()
