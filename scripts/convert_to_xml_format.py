#!/usr/bin/env python3
"""Convert Phase 8 training data from JSON code fence to Qwen3-Coder XML format.

This fixes the tool-calling format mismatch:
- Old: ```json\n{"name": "tool", "arguments": {...}}\n```
- New: <tool_call><function=tool><parameter=key>value</parameter></function></tool_call>

The XML format matches what mlx_lm.server v0.30.6 expects and can parse properly.
"""

import json
import re
from pathlib import Path


def extract_json_tool_call(content: str) -> tuple[str | None, dict | None]:
    """Extract tool name and arguments from ```json code fence.

    Args:
        content: Assistant message content with ```json fence

    Returns:
        Tuple of (tool_name, tool_args) or (None, None) if not a tool call
    """
    # Match ```json\n{...}\n```
    pattern = r"```json\n(\{[^`]+\})\n```"
    match = re.search(pattern, content)

    if not match:
        return None, None

    try:
        tool_data = json.loads(match.group(1))
        tool_name = tool_data.get("name")
        tool_args = tool_data.get("arguments", {})
        return tool_name, tool_args
    except json.JSONDecodeError:
        return None, None


def format_xml_tool_call(tool_name: str, tool_args: dict) -> str:
    """Format tool call in Qwen3-Coder XML format.

    Args:
        tool_name: Name of the tool (e.g., "run_command", "read_file")
        tool_args: Dictionary of arguments

    Returns:
        Formatted XML tool call string
    """
    # Build parameter XML tags
    params = []
    for key, value in tool_args.items():
        # Escape special characters in value
        value_str = str(value)
        params.append(f"<parameter={key}>\n{value_str}\n</parameter>")

    params_xml = "\n".join(params)

    # Build complete tool call
    return f"<tool_call>\n<function={tool_name}>\n{params_xml}\n</function>\n</tool_call>"


def convert_message(role: str, content: str) -> str:
    """Convert a single message to XML format if it's a tool call.

    Args:
        role: Message role (system, user, assistant)
        content: Message content

    Returns:
        Converted message content (XML for tool calls, unchanged otherwise)
    """
    if role == "assistant":
        # Check if this is a tool call
        tool_name, tool_args = extract_json_tool_call(content)

        if tool_name and tool_args:
            # Replace ```json fence with XML
            xml_call = format_xml_tool_call(tool_name, tool_args)
            # Keep any text before the tool call (e.g., "I'll use the X tool.")
            prefix = content.split("```json")[0].strip()
            if prefix:
                return f"{prefix}\n\n{xml_call}"
            return xml_call

    elif role == "user" and content.startswith("Tool result: "):
        # Convert tool result to <tool_response> format
        result = content.removeprefix("Tool result: ")
        return f"<tool_response>\n{result}\n</tool_response>"

    # No conversion needed
    return content


def convert_conversation(text: str) -> str:
    """Convert a full conversation from JSON to XML format.

    Args:
        text: Full conversation with <|im_start|> tokens

    Returns:
        Converted conversation with XML tool calls
    """
    # Split by message boundaries
    messages = text.split("<|im_start|>")
    converted_parts = []

    for msg in messages:
        if not msg.strip():
            continue

        # Extract role and content
        if "<|im_end|>" not in msg:
            continue

        role_and_content = msg.split("<|im_end|>")[0]
        parts = role_and_content.split("\n", 1)

        if len(parts) < 2:
            # Handle edge case: role only, no content
            converted_parts.append(f"<|im_start|>{msg}")
            continue

        role = parts[0].strip()
        content = parts[1].strip()

        # Convert content if needed
        converted_content = convert_message(role, content)

        # Reconstruct message
        converted_parts.append(f"<|im_start|>{role}\n{converted_content}<|im_end|>")

    return "\n".join(converted_parts)


def count_tool_examples(text: str) -> dict[str, int]:
    """Count tool calls vs direct answers in a conversation.

    Args:
        text: Conversation text

    Returns:
        Dict with 'tool_calls', 'direct_answers', 'total' counts
    """
    has_tool_call = "<tool_call>" in text or "```json" in text
    return {
        "tool_calls": 1 if has_tool_call else 0,
        "direct_answers": 0 if has_tool_call else 1,
        "total": 1,
    }


def main():
    input_dir = Path("data/phase8_format")
    output_dir = Path("data/phase8_xml_format")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TRAINING DATA XML CONVERTER - Phase 21 Fix")
    print("=" * 80)
    print("\nConverting from JSON code fence to Qwen3-Coder XML format")
    print("This fixes the tool-calling format mismatch in mlx_lm.server\n")

    # Track statistics
    total_stats = {"tool_calls": 0, "direct_answers": 0, "total": 0}

    # Convert each split
    for split in ["train", "valid", "test"]:
        input_file = input_dir / f"{split}.jsonl"
        output_file = output_dir / f"{split}.jsonl"

        if not input_file.exists():
            print(f"⚠️  Skipping {split}.jsonl (not found)")
            continue

        print(f"Converting {split}.jsonl...")

        converted = []
        split_stats = {"tool_calls": 0, "direct_answers": 0, "total": 0}

        with input_file.open("r") as f:
            for line in f:
                item = json.loads(line)
                original_text = item["text"]

                # Convert to XML format
                converted_text = convert_conversation(original_text)

                # Track statistics
                stats = count_tool_examples(converted_text)
                split_stats["tool_calls"] += stats["tool_calls"]
                split_stats["direct_answers"] += stats["direct_answers"]
                split_stats["total"] += stats["total"]

                converted.append({"text": converted_text})

        # Write converted data
        with output_file.open("w") as f:
            for item in converted:
                f.write(json.dumps(item) + "\n")

        # Update totals
        total_stats["tool_calls"] += split_stats["tool_calls"]
        total_stats["direct_answers"] += split_stats["direct_answers"]
        total_stats["total"] += split_stats["total"]

        print(f"  ✓ {split_stats['total']} examples")
        print(f"    - {split_stats['tool_calls']} with tool calls")
        print(f"    - {split_stats['direct_answers']} direct answers")

    print("\n" + "=" * 80)
    print("CONVERSION SUMMARY")
    print("=" * 80)
    print(f"Total examples: {total_stats['total']}")
    print(f"  With tool calls: {total_stats['tool_calls']} ({total_stats['tool_calls'] / total_stats['total'] * 100:.1f}%)")
    print(f"  Direct answers: {total_stats['direct_answers']} ({total_stats['direct_answers'] / total_stats['total'] * 100:.1f}%)")

    # Sample output for inspection
    print("\n" + "=" * 80)
    print("SAMPLE OUTPUT (first 3 examples from train)")
    print("=" * 80)

    train_file = output_dir / "train.jsonl"
    if train_file.exists():
        with train_file.open("r") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                item = json.loads(line)
                print(f"\n--- Example {i + 1} ---")
                print(item["text"][:500] + "..." if len(item["text"]) > 500 else item["text"])

    print("\n" + "=" * 80)
    print(f"✅ Converted data saved to {output_dir}")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Inspect samples above to verify XML format")
    print("  2. Run: uv run python -m mlx_lm.lora --train --data data/phase8_xml_format ...")
    print("=" * 80)


if __name__ == "__main__":
    main()
