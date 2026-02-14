#!/usr/bin/env python3
"""Convert training data to MLX-LM format - Phase 4: Domain-Specific Data.

Phase 1-3 taught tool calling patterns but with generic data.

Phase 4 strategy:
- Domain examples: ~21 examples from real t-strings repos (svcs-di, tdom-svcs, etc.)
- Public dataset (glaive): ~100 tool-calling + ~50 direct answers = ~150 examples
- POC examples: 28 Punie-specific tool examples
- Total: ~200 examples with domain-specific Python/DI/tdom patterns

The domain examples teach real-world Python patterns using actual code from projects.
The public dataset teaches the PATTERN: call → real result → interpret → answer
Our POC examples provide Punie-specific tool knowledge
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


def convert_to_qwen_format(example: dict) -> str | None:
    """Convert example to Qwen chat format with tool calls.

    Args:
        example: Dict with "query", "answer", and optional "tool_calls" fields

    Returns:
        Formatted conversation string with Qwen tokens, or None if invalid
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


def load_poc_examples() -> list[str]:
    """Load our hand-authored POC examples with real Punie tool results."""
    poc_file = Path("data/hand-authored/tool-calling/train.jsonl")
    examples = []

    if not poc_file.exists():
        print(f"⚠️  POC file not found: {poc_file}")
        return []

    with poc_file.open("r") as f:
        for line in f:
            item = json.loads(line)
            messages = item.get("messages", [])

            # Convert messages format to Qwen format
            qwen_parts = []
            for msg in messages:
                role = msg['role']
                content = msg['content']

                if role == 'system':
                    qwen_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
                elif role == 'user':
                    qwen_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
                elif role == 'assistant':
                    qwen_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")

            if qwen_parts:
                examples.append('\n'.join(qwen_parts))

    return examples


def load_domain_examples() -> list[str]:
    """Load domain-specific examples from t-strings repos."""
    domain_file = Path("data/domain_examples.jsonl")
    examples = []

    if not domain_file.exists():
        print(f"⚠️  Domain file not found: {domain_file}")
        return []

    with domain_file.open("r") as f:
        for line in f:
            item = json.loads(line)
            messages = item.get("messages", [])

            # Convert messages format to Qwen format
            qwen_parts = []
            for msg in messages:
                role = msg['role']
                content = msg['content']

                if role == 'system':
                    qwen_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
                elif role == 'user':
                    qwen_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
                elif role == 'assistant':
                    qwen_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")

            if qwen_parts:
                examples.append('\n'.join(qwen_parts))

    return examples


def main():
    output_dir = Path("data/mlx_format")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TRAINING DATA CONVERTER - Phase 4: Domain-Specific Data")
    print("=" * 80)

    # 1. Load domain-specific examples (HIGHEST PRIORITY)
    print("\n✓ Loading domain examples from t-strings repos...")
    domain_examples = load_domain_examples()
    print(f"  Loaded {len(domain_examples)} domain examples")

    # 2. Load public dataset (converted by convert_public_datasets.py)
    # Limit to 150 examples to keep focus on domain data
    public_file = Path("data/public_dataset_converted.jsonl")
    public_examples = []

    if public_file.exists():
        print(f"\n✓ Loading public dataset from {public_file}...")
        with public_file.open("r") as f:
            for line in f:
                item = json.loads(line)
                public_examples.append(item['text'])
        # Limit public examples to 150 (100 tool + 50 direct)
        if len(public_examples) > 150:
            random.seed(42)
            public_examples = random.sample(public_examples, 150)
        print(f"  Loaded {len(public_examples)} public examples (sampled)")
    else:
        print(f"\n⚠️  Public dataset not found at {public_file}")
        print("   Continuing without public data...")

    # 3. Load our POC examples with Punie tools
    print("\n✓ Loading POC examples...")
    poc_examples = load_poc_examples()
    print(f"  Loaded {len(poc_examples)} POC examples with Punie tools")

    # 4. Load generated Q&A (non-tool examples) - SKIP for now
    generated_file = Path("data/training_examples_1k.jsonl")
    generated_examples = []

    if generated_file.exists():
        print(f"\n✓ Loading generated Q&A from {generated_file}...")
        with generated_file.open("r") as f:
            for line in f:
                example = json.loads(line)
                # Only include examples WITHOUT tool calls
                if not example.get("tool_calls"):
                    text = convert_to_qwen_format(example)
                    if text:
                        generated_examples.append(text)

        # Limit to 20 examples
        if len(generated_examples) > 20:
            random.seed(42)
            generated_examples = random.sample(generated_examples, 20)
        print(f"  Loaded {len(generated_examples)} simple Q&A examples")
    else:
        print(f"\n⚠️  Generated examples not found at {generated_file}")

    # 5. Combine all sources
    all_examples = []
    all_examples.extend(domain_examples)
    all_examples.extend(poc_examples)
    all_examples.extend(public_examples)
    all_examples.extend(generated_examples)

    print("\n✓ Combined dataset:")
    print(f"  Domain (t-strings repos): {len(domain_examples)}")
    print(f"  POC (Punie-specific tools): {len(poc_examples)}")
    print(f"  Public (tool-calling patterns): {len(public_examples)}")
    print(f"  Generated (simple Q&A): {len(generated_examples)}")
    print(f"  Total: {len(all_examples)}")

    # 6. Shuffle all examples
    random.seed(42)
    random.shuffle(all_examples)

    # 7. Split 90/10
    split_idx = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_idx]
    valid_examples = all_examples[split_idx:]

    print("\n✓ Split 90/10:")
    print(f"  Train: {len(train_examples)} examples")
    print(f"  Valid: {len(valid_examples)} examples")

    # 8. Write train set
    train_file = output_dir / "train.jsonl"
    with train_file.open("w") as f:
        for text in train_examples:
            f.write(json.dumps({"text": text}) + "\n")

    # 9. Write valid set
    valid_file = output_dir / "valid.jsonl"
    with valid_file.open("w") as f:
        for text in valid_examples:
            f.write(json.dumps({"text": text}) + "\n")

    print("\n✅ Training data saved:")
    print(f"  {train_file} ({len(train_examples)} examples)")
    print(f"  {valid_file} ({len(valid_examples)} examples)")
    print("\n📝 Format: {{text: ...}} with Qwen chat tokens")
    print("   Same format that worked in Phase 1-3")
    print("\n✅ Dataset includes:")
    print(f"  • {len(domain_examples)} domain-specific examples (svcs-di, tdom-svcs, etc.)")
    print(f"  • {len(poc_examples)} Punie-specific tool examples")
    print(f"  • {len(public_examples)} generic tool-calling patterns")
    print(f"  • {len(generated_examples)} simple Q&A (no tools)")
    print("\n🎯 Model should learn:")
    print("  1. Real Python/DI/tdom patterns from domain examples")
    print("  2. How to interpret real tool results (not placeholders)")
    print("  3. When to stop calling tools and give final answer")
    print("  4. When NOT to use tools (direct answers)")
    print("\n✓ Next: Train with this dataset using 300 iters, batch_size 2")
    print("=" * 80)


if __name__ == "__main__":
    main()
