#!/usr/bin/env python3
"""Download and convert public tool-calling datasets to our format.

Phase 3: Use glaive-function-calling-v2 dataset to teach the model:
- How to interpret real tool results (not placeholders)
- When to stop calling tools and give a final answer
- When NOT to use tools (direct answers)

The glaive dataset has 113k examples with multi-turn conversations showing:
USER → ASSISTANT calls tool → FUNCTION RESPONSE → ASSISTANT answers
"""

import json
import random
import re
from pathlib import Path

from datasets import load_dataset


def parse_glaive_conversation(text: str) -> list[dict] | None:
    """Parse a glaive conversation into structured messages.

    Glaive format:
        SYSTEM: You are a helpful assistant...
        USER: What's the weather?
        ASSISTANT: <functioncall> {"name": "get_weather", ...}
        FUNCTION RESPONSE: {"temperature": 72, ...}
        ASSISTANT: It's 72 degrees.

    Returns:
        List of messages with role and content, or None if parse fails
    """
    messages = []

    # Split by double newlines first to get distinct message blocks
    blocks = text.split('\n\n')

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Check which role this block starts with
        if block.startswith('SYSTEM:'):
            content = block[7:].strip()  # Remove "SYSTEM:"
            messages.append({'role': 'SYSTEM', 'content': content})
        elif block.startswith('USER:'):
            content = block[5:].strip()  # Remove "USER:"
            # Remove trailing <|endoftext|>
            content = content.replace('<|endoftext|>', '').strip()
            messages.append({'role': 'USER', 'content': content})
        elif block.startswith('ASSISTANT:'):
            content = block[10:].strip()  # Remove "ASSISTANT:"
            # Remove trailing <|endoftext|>
            content = content.replace('<|endoftext|>', '').strip()
            messages.append({'role': 'ASSISTANT', 'content': content})
        elif block.startswith('FUNCTION RESPONSE:'):
            content = block[18:].strip()  # Remove "FUNCTION RESPONSE:"
            content = content.replace('<|endoftext|>', '').strip()
            messages.append({'role': 'FUNCTION RESPONSE', 'content': content})

    return messages if messages else None


def has_tool_pattern(messages: list[dict]) -> bool:
    """Check if conversation has tool call → result → answer pattern."""
    for i in range(len(messages) - 2):
        msg = messages[i]
        next_msg = messages[i + 1]
        final_msg = messages[i + 2]

        # Look for: ASSISTANT with <functioncall> → FUNCTION RESPONSE → ASSISTANT
        if (msg['role'] == 'ASSISTANT' and '<functioncall>' in msg['content'] and
            next_msg['role'] == 'FUNCTION RESPONSE' and
            final_msg['role'] == 'ASSISTANT'):
            return True

    return False


def convert_to_qwen_format(messages: list[dict]) -> str | None:
    """Convert glaive messages to Qwen chat format.

    Maps:
        SYSTEM → <|im_start|>system\n...<|im_end|>
        USER → <|im_start|>user\n...<|im_end|>
        ASSISTANT (with <functioncall>) → <|im_start|>assistant\nI'll use the X tool.\n\n```json\n{...}\n```<|im_end|>
        FUNCTION RESPONSE → <|im_start|>user\nTool result: ...<|im_end|>
        ASSISTANT (normal) → <|im_start|>assistant\n...<|im_end|>

    Returns:
        Formatted conversation string, or None if conversion fails
    """
    qwen_messages = []

    for msg in messages:
        role = msg['role']
        content = msg['content']

        if role == 'SYSTEM':
            # Replace glaive system prompt with Punie's
            qwen_messages.append(
                "<|im_start|>system\nYou are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>"
            )

        elif role == 'USER':
            qwen_messages.append(f"<|im_start|>user\n{content}<|im_end|>")

        elif role == 'ASSISTANT':
            # Check if this is a tool call
            if '<functioncall>' in content:
                # Extract everything after <functioncall> as the JSON
                json_start = content.find('<functioncall>') + len('<functioncall>')
                json_str = content[json_start:].strip()

                try:
                    # The glaive format uses: {"name": "X", "arguments": '{...}'}
                    # where arguments is a JSON string with single quotes
                    # Extract name and arguments separately
                    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', json_str)
                    if not name_match:
                        return None

                    tool_name = name_match.group(1)

                    # Extract arguments - it's a quoted string that may contain nested quotes
                    args_match = re.search(r'"arguments"\s*:\s*[\'"](.+?)[\'"](?:\s*})', json_str, re.DOTALL)
                    if args_match:
                        # Arguments is a JSON string - parse it
                        args_str = args_match.group(1)
                        # Fix escaped quotes
                        args_str = args_str.replace('\\"', '"')
                        try:
                            arguments = json.loads(args_str)
                        except (json.JSONDecodeError, ValueError):
                            # If it's not valid JSON, use it as is
                            arguments = args_str
                    else:
                        # No arguments or null
                        arguments = {}

                    # Build the function call object
                    func_data = {"name": tool_name, "arguments": arguments}

                    # Format as our tool call style
                    qwen_messages.append(
                        f"<|im_start|>assistant\nI'll use the {tool_name} tool.\n\n```json\n{json.dumps(func_data, indent=2)}\n```<|im_end|>"
                    )
                except Exception:
                    # Any parsing error, skip this example
                    return None
            else:
                # Normal assistant response
                qwen_messages.append(f"<|im_start|>assistant\n{content}<|im_end|>")

        elif role == 'FUNCTION RESPONSE':
            # Wrap as tool result
            qwen_messages.append(f"<|im_start|>user\nTool result: {content}<|im_end|>")

    return '\n'.join(qwen_messages)


def filter_example(messages: list[dict], max_tokens: int = 2048) -> bool:
    """Check if example meets quality criteria.

    Criteria:
    - Has at least one tool call with result and final answer OR is a simple Q&A
    - Reasonable length (not too long for context window)
    - Well-formed structure
    """
    # Check length (rough estimate: ~4 chars per token)
    text_length = sum(len(m['content']) for m in messages)
    if text_length > max_tokens * 4:
        return False

    # Must have system, user, and at least one assistant message
    roles = [m['role'] for m in messages]
    if 'SYSTEM' not in roles or 'USER' not in roles or 'ASSISTANT' not in roles:
        return False

    # Either has tool pattern OR is simple Q&A (no function calls)
    has_tools = any('<functioncall>' in m['content'] for m in messages if m['role'] == 'ASSISTANT')

    if has_tools:
        # Must have complete pattern: tool call → result → answer
        return has_tool_pattern(messages)
    else:
        # Simple Q&A: just user question + assistant answer (with system)
        # Count user and assistant turns
        user_count = sum(1 for m in messages if m['role'] == 'USER')
        assistant_count = sum(1 for m in messages if m['role'] == 'ASSISTANT')

        # Accept single turn (1 user + 1 assistant) or short multi-turn (max 3 user turns)
        # This catches simple Q&A and also multi-turn conversations without tools
        return user_count <= 3 and user_count == assistant_count and text_length < 3000


def main():
    print("=" * 80)
    print("PUBLIC DATASET CONVERTER - Phase 3")
    print("=" * 80)
    print("\nDownloading glaive-function-calling-v2 dataset...")
    print("(This may take a few minutes on first run)")

    # Load dataset from HuggingFace
    dataset = load_dataset("glaiveai/glaive-function-calling-v2", split="train")
    print(f"✓ Loaded {len(dataset)} examples")

    # Process examples - separate passes for tool-calling and direct answers
    print("\nProcessing tool-calling examples...")
    tool_calling_examples = []
    skipped_tools = 0

    for item in dataset:
        # Only look for examples with function calls
        if '<functioncall>' not in item['chat']:
            continue

        # Parse conversation
        messages = parse_glaive_conversation(item['system'] + '\n\n' + item['chat'])

        if not messages:
            skipped_tools += 1
            continue

        # Filter by quality
        if not filter_example(messages):
            skipped_tools += 1
            continue

        # Convert to Qwen format
        qwen_text = convert_to_qwen_format(messages)
        if not qwen_text:
            skipped_tools += 1
            continue

        tool_calling_examples.append(qwen_text)

        # Stop when we have enough tool examples
        if len(tool_calling_examples) >= 350:
            break

    print(f"  Collected {len(tool_calling_examples)} tool-calling examples (skipped {skipped_tools})")

    # Now collect direct answer examples
    print("\nProcessing direct-answer examples...")
    direct_answer_examples = []
    skipped_direct = 0

    for item in dataset:
        # Only look for examples WITHOUT function calls
        if '<functioncall>' in item['chat']:
            continue

        # Parse conversation
        messages = parse_glaive_conversation(item['system'] + '\n\n' + item['chat'])

        if not messages:
            skipped_direct += 1
            continue

        # Filter by quality
        if not filter_example(messages):
            skipped_direct += 1
            continue

        # Convert to Qwen format
        qwen_text = convert_to_qwen_format(messages)
        if not qwen_text:
            skipped_direct += 1
            continue

        direct_answer_examples.append(qwen_text)

        # Stop when we have enough direct examples
        if len(direct_answer_examples) >= 100:
            break

    print(f"  Collected {len(direct_answer_examples)} direct-answer examples (skipped {skipped_direct})")

    skipped = skipped_tools + skipped_direct

    print("\n✓ Processed examples:")
    print(f"  Tool-calling (with results): {len(tool_calling_examples)}")
    print(f"  Direct answers (no tools): {len(direct_answer_examples)}")
    print(f"  Skipped (quality/parse issues): {skipped}")

    # Sample to target counts
    random.seed(42)

    # Take up to 350 tool-calling (leave room for our POC examples)
    if len(tool_calling_examples) > 350:
        tool_calling_examples = random.sample(tool_calling_examples, 350)

    # Take up to 100 direct answers
    if len(direct_answer_examples) > 100:
        direct_answer_examples = random.sample(direct_answer_examples, 100)

    print("\n✓ Sampled:")
    print(f"  Tool-calling: {len(tool_calling_examples)}")
    print(f"  Direct answers: {len(direct_answer_examples)}")
    print(f"  Total: {len(tool_calling_examples) + len(direct_answer_examples)}")

    # Save to intermediate file
    output_file = Path("data/public_dataset_converted.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    all_examples = []
    for text in tool_calling_examples:
        all_examples.append({'text': text, 'source': 'glaive_tools'})
    for text in direct_answer_examples:
        all_examples.append({'text': text, 'source': 'glaive_direct'})

    # Shuffle combined
    random.shuffle(all_examples)

    with output_file.open('w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + '\n')

    print(f"\n✅ Saved to {output_file}")
    print(f"   {len(all_examples)} examples in {'{text, source}'} format")

    # Show sample
    print("\n📋 Sample converted example:")
    print("-" * 80)
    sample = random.choice(tool_calling_examples)
    print(sample[:500] + "..." if len(sample) > 500 else sample)
    print("-" * 80)

    print("\n✓ Next step: Run scripts/convert_training_data.py to merge with POC examples")
    print("=" * 80)


if __name__ == "__main__":
    main()
