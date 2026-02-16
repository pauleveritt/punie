#!/usr/bin/env python3
"""Convert Phase 24 ruff/pytest examples from Format B to Format A.

Format B (current Phase 24):
  - Messages format but NO system message
  - Bare <tool_call> without XML wrapper
  - Example: <tool_call>\nresult = ruff_check("src/")\n</tool_call>

Format A (target for Phase 26):
  - Messages format WITH system message
  - XML wrapper: <tool_call><function=execute_code><parameter=code>
  - Example: <tool_call><function=execute_code><parameter=code>\nresult = ruff_check("src/")\n</parameter></function></tool_call>

This conversion ensures Phase 24 examples (which DO show field access) can be
included in Phase 26 training with consistent formatting.
"""

import json
from pathlib import Path

# Constants
RUFF_INPUT = Path("data/ruff_training/ruff_examples.jsonl")
PYTEST_INPUT = Path("data/pytest_training/pytest_examples.jsonl")
OUTPUT_DIR = Path("data/phase24_format_a")
SYSTEM_PROMPT = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."


def extract_code_from_format_b(content: str) -> str | None:
    """Extract Python code from Format B tool call.

    Args:
        content: Assistant message content with Format B tool call

    Returns:
        Extracted Python code or None if not a tool call
    """
    # Format B: <tool_call>\nCODE HERE\n</tool_call>
    if not content.strip().startswith("<tool_call>"):
        return None

    # Remove <tool_call> and </tool_call> markers
    code = content.replace("<tool_call>", "").replace("</tool_call>", "").strip()
    return code


def wrap_code_in_format_a(code: str) -> str:
    """Wrap Python code in Format A XML structure.

    Args:
        code: Python code to wrap

    Returns:
        Format A XML-wrapped tool call
    """
    return f"""<tool_call><function=execute_code>
<parameter=code>
{code}
</parameter>
</function></tool_call>"""


def convert_example(example: dict) -> dict:
    """Convert a single example from Format B to Format A.

    Args:
        example: Dict with "messages" list

    Returns:
        Converted example with system message and XML-wrapped code
    """
    messages = example.get("messages", [])

    # Build new messages list with system message
    new_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        # If this is an assistant message with a tool call, convert it
        if role == "assistant" and "<tool_call>" in content:
            code = extract_code_from_format_b(content)
            if code:
                # Wrap in Format A XML
                new_content = wrap_code_in_format_a(code)
                new_messages.append({"role": "assistant", "content": new_content})
            else:
                # Keep original if extraction failed
                new_messages.append(msg)
        else:
            # Keep non-tool-call messages as-is
            new_messages.append(msg)

    return {"messages": new_messages}


def convert_file(input_path: Path, output_path: Path) -> int:
    """Convert a JSONL file from Format B to Format A.

    Args:
        input_path: Path to input JSONL file (Format B)
        output_path: Path to output JSONL file (Format A)

    Returns:
        Number of examples converted
    """
    examples = []

    with input_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                example = json.loads(line)
                converted = convert_example(example)
                examples.append(converted)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping malformed line: {e}")
                continue

    # Write converted examples
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    return len(examples)


def main():
    """Convert Phase 24 ruff and pytest examples to Format A."""
    print("Converting Phase 24 examples from Format B to Format A...")
    print()

    total_converted = 0

    # Convert ruff examples
    if RUFF_INPUT.exists():
        print(f"Converting ruff examples: {RUFF_INPUT}")
        ruff_output = OUTPUT_DIR / "ruff_examples.jsonl"
        count = convert_file(RUFF_INPUT, ruff_output)
        print(f"  Converted {count} examples → {ruff_output}")
        total_converted += count
    else:
        print(f"Warning: {RUFF_INPUT} not found")

    # Convert pytest examples
    if PYTEST_INPUT.exists():
        print(f"\nConverting pytest examples: {PYTEST_INPUT}")
        pytest_output = OUTPUT_DIR / "pytest_examples.jsonl"
        count = convert_file(PYTEST_INPUT, pytest_output)
        print(f"  Converted {count} examples → {pytest_output}")
        total_converted += count
    else:
        print(f"Warning: {PYTEST_INPUT} not found")

    print()
    print(f"{'='*60}")
    print(f"Total examples converted: {total_converted}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
