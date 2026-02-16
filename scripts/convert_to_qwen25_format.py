#!/usr/bin/env python3
"""
Convert Phase 24 training data from Qwen3 XML format to Qwen2.5 JSON format.

Handles:
- Format A: <function=execute_code><parameter=code>...</parameter></function>
- Format B: <tool_call>bare Python code</tool_call>
- Direct answers: No changes needed

Converts both to: <tool_call>{"name": "execute_code", "arguments": {"code": "..."}}</tool_call>
"""

import json
import re
from pathlib import Path
from typing import Counter

# Qwen2.5 system prompt with tool definitions
QWEN25_SYSTEM_PROMPT = """You are Punie, an AI coding assistant that helps with Python development via PyCharm.

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": {"name": "execute_code", "description": "Execute Python code. Available functions: read_file(path), write_file(path, content), run_command(command), typecheck(path), ruff_check(path), pytest_run(path). Use print() to show output.", "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "Python code to execute"}}, "required": ["code"]}}}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>"""


def extract_code_from_xml(tool_call_content: str) -> str | None:
    """Extract Python code from Format A XML structure."""
    # Match <parameter=code>...</parameter>
    match = re.search(r'<parameter=code>\s*(.*?)\s*</parameter>', tool_call_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def extract_bare_python(tool_call_content: str) -> str | None:
    """Extract Python code from Format B (bare Python after <tool_call>)."""
    # Remove <function=execute_code> wrapper if present
    content = re.sub(r'^<function=execute_code>\s*', '', tool_call_content)
    content = re.sub(r'\s*</function>$', '', content)

    # If it looks like Python code (not XML), return it
    if not content.strip().startswith('<'):
        return content.strip()

    return None


def convert_tool_call(assistant_message: str) -> tuple[str, str]:
    """
    Convert a tool call from XML to JSON format.

    Returns: (converted_message, format_type)
    format_type is one of: 'format_a', 'format_b', 'direct_answer'
    """
    if '<tool_call>' not in assistant_message:
        return assistant_message, 'direct_answer'

    # Extract everything inside <tool_call>...</tool_call>
    tool_call_match = re.search(r'<tool_call>(.*?)</tool_call>', assistant_message, re.DOTALL)
    if not tool_call_match:
        return assistant_message, 'direct_answer'

    tool_call_content = tool_call_match.group(1)

    # Try Format A (XML with parameter tags)
    code = extract_code_from_xml(tool_call_content)
    if code:
        json_tool_call = json.dumps({
            "name": "execute_code",
            "arguments": {"code": code}
        })
        converted = assistant_message.replace(
            tool_call_match.group(0),
            f'<tool_call>\n{json_tool_call}\n</tool_call>'
        )
        return converted, 'format_a'

    # Try Format B (bare Python)
    code = extract_bare_python(tool_call_content)
    if code:
        json_tool_call = json.dumps({
            "name": "execute_code",
            "arguments": {"code": code}
        })
        converted = assistant_message.replace(
            tool_call_match.group(0),
            f'<tool_call>\n{json_tool_call}\n</tool_call>'
        )
        return converted, 'format_b'

    # Couldn't parse - leave as-is
    return assistant_message, 'unknown'


def convert_example(example: dict) -> dict:
    """Convert a single training example from Qwen3 to Qwen2.5 format."""
    text = example['text']

    # Split into messages
    parts = text.split('<|im_start|>')
    converted_parts = []

    for part in parts:
        if not part.strip():
            continue

        # Extract role and content
        if '<|im_end|>' not in part:
            continue

        content = part.split('<|im_end|>')[0]

        # Check role
        if content.startswith('system\n'):
            # Replace with Qwen2.5 system prompt
            role_content = QWEN25_SYSTEM_PROMPT
            converted_parts.append(f'<|im_start|>system\n{role_content}<|im_end|>')

        elif content.startswith('assistant\n'):
            # Convert tool calls in assistant messages
            assistant_content = content[len('assistant\n'):]
            converted_content, _ = convert_tool_call(assistant_content)
            converted_parts.append(f'<|im_start|>assistant\n{converted_content}<|im_end|>')

        else:
            # Keep user messages and tool_response as-is
            converted_parts.append(f'<|im_start|>{content}<|im_end|>')

    return {'text': '\n'.join(converted_parts)}


def analyze_format_distribution(input_file: Path) -> dict[str, int]:
    """Analyze the distribution of formats in a JSONL file."""
    format_counter = Counter()

    with open(input_file) as f:
        for line in f:
            example = json.loads(line)
            text = example['text']

            # Look for tool calls in assistant messages
            assistant_messages = re.findall(r'<|im_start|>assistant\n(.*?)<|im_end|>', text, re.DOTALL)

            for msg in assistant_messages:
                if '<tool_call>' not in msg:
                    format_counter['direct_answer'] += 1
                    continue

                # Extract tool call content
                tool_call_match = re.search(r'<tool_call>(.*?)</tool_call>', msg, re.DOTALL)
                if not tool_call_match:
                    continue

                content = tool_call_match.group(1)

                # Detect format
                if '<parameter=code>' in content:
                    format_counter['format_a'] += 1
                elif '<function=execute_code>' not in content and not content.strip().startswith('<'):
                    format_counter['format_b'] += 1
                else:
                    format_counter['unknown'] += 1

    return dict(format_counter)


def convert_file(input_file: Path, output_file: Path) -> dict:
    """Convert a JSONL file and return statistics."""
    stats = Counter()

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(input_file) as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            example = json.loads(line)
            converted = convert_example(example)

            # Track format changes
            text = example['text']
            assistant_messages = re.findall(r'<|im_start|>assistant\n(.*?)<|im_end|>', text, re.DOTALL)

            for msg in assistant_messages:
                _, format_type = convert_tool_call(msg)
                stats[format_type] += 1

            f_out.write(json.dumps(converted) + '\n')

    return dict(stats)


def verify_conversion(input_file: Path, output_file: Path, num_samples: int = 5):
    """Verify conversion by spot-checking random examples."""
    import random

    # Read all examples
    with open(output_file) as f:
        examples = [json.loads(line) for line in f]

    # Sample random examples
    samples = random.sample(examples, min(num_samples, len(examples)))

    print(f"\n{'='*80}")
    print(f"SPOT CHECK: {num_samples} random examples from {output_file.name}")
    print(f"{'='*80}\n")

    for i, example in enumerate(samples, 1):
        text = example['text']
        print(f"--- Example {i} ---")

        # Check for XML fragments (should be gone)
        if '<parameter=' in text or '<function=' in text:
            print("⚠️  WARNING: XML fragments still present!")

        # Check for JSON tool calls
        if '"name": "execute_code"' in text:
            print("✓ JSON tool call format detected")

        # Check for tool_response
        if '<tool_response>' in text:
            print("✓ tool_response preserved")

        # Show first 200 chars
        print(f"Preview: {text[:200]}...")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert Phase 24 data to Qwen2.5 format')
    parser.add_argument('--input-dir', type=Path, default=Path('data/phase24_merged'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/phase25b_qwen25_format'))
    parser.add_argument('--verify', action='store_true', help='Spot-check converted examples')

    args = parser.parse_args()

    # Analyze input distribution
    print("Analyzing input format distribution...")
    for split in ['train', 'valid', 'test']:
        input_file = args.input_dir / f'{split}.jsonl'
        if input_file.exists():
            dist = analyze_format_distribution(input_file)
            print(f"\n{split}.jsonl:")
            for format_type, count in sorted(dist.items()):
                print(f"  {format_type}: {count}")

    # Convert files
    print("\n" + "="*80)
    print("Converting files...")
    print("="*80 + "\n")

    total_stats = Counter()
    for split in ['train', 'valid', 'test']:
        input_file = args.input_dir / f'{split}.jsonl'
        output_file = args.output_dir / f'{split}.jsonl'

        if not input_file.exists():
            continue

        print(f"Converting {input_file.name}...")
        stats = convert_file(input_file, output_file)

        for format_type, count in stats.items():
            total_stats[format_type] += count

        print(f"  → {output_file}")
        print(f"     {sum(stats.values())} examples processed")

    # Print summary
    print("\n" + "="*80)
    print("CONVERSION SUMMARY")
    print("="*80)
    print("\nTotal examples by format:")
    for format_type, count in sorted(total_stats.items()):
        print(f"  {format_type}: {count}")

    # Verification
    if args.verify:
        for split in ['train', 'valid', 'test']:
            input_file = args.input_dir / f'{split}.jsonl'
            output_file = args.output_dir / f'{split}.jsonl'

            if output_file.exists():
                verify_conversion(input_file, output_file)

    print("\n✅ Conversion complete!")
    print(f"Output directory: {args.output_dir}")


if __name__ == '__main__':
    main()
