#!/usr/bin/env python3
"""Convert Phase 21 XML training data to Phase 22 Code Mode format.

This converts single-tool XML calls to execute_code Python format:
- Old: <tool_call><function=read_file><parameter=path>test.py</parameter></function></tool_call>
- New: <tool_call><function=execute_code><parameter=code>
       result = read_file("test.py")
       print(result)
       </parameter></function></tool_call>

Direct-answer examples (no tool calls) remain unchanged.
"""

import json
import re
from pathlib import Path


def extract_xml_tool_call(content: str) -> tuple[str | None, dict | None]:
    """Extract tool name and parameters from XML tool call.

    Args:
        content: Assistant message content with XML tool call

    Returns:
        Tuple of (tool_name, tool_params) or (None, None) if not a tool call
    """
    # Match <tool_call><function=NAME>...<parameter=KEY>VALUE</parameter>...</function></tool_call>
    tool_pattern = r"<tool_call>\s*<function=(\w+)>(.*?)</function>\s*</tool_call>"
    match = re.search(tool_pattern, content, re.DOTALL)

    if not match:
        return None, None

    tool_name = match.group(1)
    params_content = match.group(2)

    # Extract parameters
    param_pattern = r"<parameter=(\w+)>(.*?)</parameter>"
    params = {}
    for param_match in re.finditer(param_pattern, params_content, re.DOTALL):
        key = param_match.group(1)
        value = param_match.group(2).strip()
        params[key] = value

    return tool_name, params


def format_python_value(value: str, param_name: str) -> str:
    """Format a parameter value as Python literal.

    Args:
        value: String value from XML parameter
        param_name: Parameter name (for context)

    Returns:
        Python literal representation (string, list, or None)
    """
    # If it looks like a list (contains brackets), try to parse as JSON
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
            return repr(parsed)
        except json.JSONDecodeError:
            pass

    # Otherwise treat as string
    return repr(value)


def convert_to_python_code(tool_name: str, tool_params: dict) -> str:
    """Convert XML tool call to Python code.

    Args:
        tool_name: Name of the tool (read_file, write_file, run_command)
        tool_params: Dictionary of parameters

    Returns:
        Python code string that calls the function and prints output
    """
    if tool_name == "read_file":
        path = tool_params.get("path", "")
        return f"""result = read_file({format_python_value(path, "path")})
print(result)"""

    elif tool_name == "write_file":
        path = tool_params.get("path", "")
        content = tool_params.get("content", "")
        return f"""result = write_file({format_python_value(path, "path")}, {format_python_value(content, "content")})
print(result)"""

    elif tool_name == "run_command":
        command = tool_params.get("command", "")
        args = tool_params.get("args")
        cwd = tool_params.get("cwd")

        # Build function call with optional parameters
        call_parts = [f"{format_python_value(command, 'command')}"]
        if args:
            call_parts.append(f"args={format_python_value(args, 'args')}")
        if cwd:
            call_parts.append(f"cwd={format_python_value(cwd, 'cwd')}")

        call_str = ", ".join(call_parts)
        return f"""result = run_command({call_str})
print(result)"""

    else:
        # Unknown tool - return generic code
        return f"""# Unknown tool: {tool_name}
print("Tool not supported in code mode")"""


def format_execute_code_xml(python_code: str) -> str:
    """Format Python code in execute_code XML wrapper.

    Args:
        python_code: Python source code to wrap

    Returns:
        Formatted XML execute_code call
    """
    return f"""<tool_call><function=execute_code>
<parameter=code>
{python_code}
</parameter>
</function></tool_call>"""


def convert_message(role: str, content: str) -> str:
    """Convert a single message to Code Mode format if it's a tool call.

    Args:
        role: Message role (system, user, assistant)
        content: Message content

    Returns:
        Converted message content (Code Mode for tool calls, unchanged otherwise)
    """
    if role == "assistant":
        # Check if this is a tool call
        tool_name, tool_params = extract_xml_tool_call(content)

        if tool_name and tool_params:
            # Convert to Python code + execute_code wrapper
            python_code = convert_to_python_code(tool_name, tool_params)
            code_xml = format_execute_code_xml(python_code)

            # Keep any text before the tool call (e.g., "I'll use the X tool.")
            prefix = content.split("<tool_call>")[0].strip()
            if prefix:
                return f"{prefix}\n\n{code_xml}"
            return code_xml

    elif role == "user" and "<tool_response>" in content:
        # Tool responses stay as-is in Code Mode
        return content

    # No conversion needed (direct answers, system prompts, etc.)
    return content


def convert_conversation(text: str) -> str:
    """Convert a full conversation from XML to Code Mode format.

    Args:
        text: Full conversation with <|im_start|> tokens

    Returns:
        Converted conversation
    """
    # Split by message boundaries
    messages = text.split("<|im_start|>")
    converted = []

    for msg in messages:
        if not msg.strip():
            continue

        # Split role and content
        parts = msg.split("\n", 1)
        if len(parts) != 2:
            continue

        role = parts[0].strip()
        content = parts[1].replace("<|im_end|>", "").strip()

        # Convert message
        converted_content = convert_message(role, content)

        # Reconstruct message
        converted.append(f"<|im_start|>{role}\n{converted_content}<|im_end|>")

    return "\n".join(converted)


def convert_file(input_path: Path, output_path: Path) -> int:
    """Convert a JSONL file from XML to Code Mode format.

    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSONL file

    Returns:
        Number of examples converted
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with input_path.open() as f_in, output_path.open("w") as f_out:
        for line in f_in:
            example = json.loads(line)
            original_text = example["text"]

            # Convert conversation
            converted_text = convert_conversation(original_text)

            # Write converted example
            converted_example = {"text": converted_text}
            f_out.write(json.dumps(converted_example) + "\n")
            count += 1

    return count


def main():
    """Convert all Phase 21 training data to Code Mode format."""
    # Paths
    input_dir = Path("data/phase8_xml_format")
    output_dir = Path("data/phase22_code_format")

    print("Converting Phase 21 XML to Phase 22 Code Mode format...")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print()

    # Convert each split
    total = 0
    for split in ["train", "valid", "test"]:
        input_file = input_dir / f"{split}.jsonl"
        output_file = output_dir / f"{split}.jsonl"

        if not input_file.exists():
            print(f"⚠️  Skipping {split} (file not found)")
            continue

        count = convert_file(input_file, output_file)
        print(f"✓ Converted {split}: {count} examples")
        total += count

    print()
    print(f"Total: {total} examples converted to Code Mode format")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
