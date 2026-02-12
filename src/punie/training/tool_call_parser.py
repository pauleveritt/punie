"""Tool call parsing utilities for training pipeline.

This module extracts tool calls from model output text, supporting both
JSON and XML formats commonly used by different language models.

Supported formats:
1. JSON: <tool_call>{"name": "function_name", "arguments": {...}}</tool_call>
2. XML: <tool_call><function=name><parameter=key>value</parameter></function></tool_call>
3. Broken XML (missing opening tag): <function=name>...</function></tool_call>
"""

from __future__ import annotations

import json
import re
from typing import Any


def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract tool calls from model output.

    Supports two formats:
    1. JSON: <tool_call>{"name": "function_name", "arguments": {...}}</tool_call>
    2. XML: <tool_call><function=name><parameter=key>value</parameter></function></tool_call>

    Args:
        text: Model output possibly containing tool call blocks

    Returns:
        Tuple of (remaining_text, list of tool call dicts)
        Each dict has 'name' and optionally 'arguments' keys.
    """
    calls: list[dict[str, Any]] = []
    clean_text = text
    patterns_to_remove: list[tuple[int, int]] = []

    # Pattern 1: Standard <tool_call>...</tool_call> blocks
    pattern = r"<tool_call>(.*?)</tool_call>"
    matches = re.finditer(pattern, text, re.DOTALL)

    for match in matches:
        match_stripped = match.group(1).strip()
        parsed_successfully = False

        # Try JSON format first
        if match_stripped.startswith("{"):
            try:
                call = json.loads(match_stripped)
                if "name" in call:
                    calls.append(call)
                    parsed_successfully = True
            except json.JSONDecodeError:
                pass

        # Try XML format if JSON failed: <function=name><parameter=key>value</parameter></function>
        if not parsed_successfully:
            xml_call = _parse_xml_tool_call(match_stripped)
            if xml_call:
                calls.append(xml_call)
                parsed_successfully = True

        # Always remove the tool_call tags, even if parsing failed
        patterns_to_remove.append((match.start(), match.end()))

    # Pattern 2: Broken format without opening <tool_call> tag
    # Some models output: <function=name>...</function></tool_call>
    broken_pattern = r"<function=([^>]+)>(.*?)</function>\s*</tool_call>"
    broken_matches = re.finditer(broken_pattern, text, re.DOTALL)

    for match in broken_matches:
        # Check if this match overlaps with any already-found matches
        start, end = match.start(), match.end()
        overlaps = any(s <= start < e or s < end <= e for s, e in patterns_to_remove)
        if overlaps:
            continue

        func_name = match.group(1)
        params_block = match.group(2)
        xml_call = _parse_xml_function_block(func_name, params_block)
        if xml_call:
            calls.append(xml_call)
            patterns_to_remove.append((start, end))

    # Remove matched patterns from text (in reverse order to preserve indices)
    patterns_to_remove.sort(reverse=True)
    for start, end in patterns_to_remove:
        clean_text = clean_text[:start] + clean_text[end:]

    clean_text = clean_text.strip()

    return clean_text, calls


def _parse_xml_tool_call(xml_content: str) -> dict[str, Any] | None:
    """Parse XML-format tool call.

    Expected format: <function=name><parameter=key>value</parameter></function>

    Args:
        xml_content: XML content inside <tool_call> tags

    Returns:
        Tool call dict with 'name' and 'arguments' keys, or None if parsing fails
    """
    # Extract function name
    func_match = re.search(r"<function=([^>]+)>", xml_content)
    if not func_match:
        return None

    func_name = func_match.group(1).strip()

    # Extract parameters
    param_pattern = r"<parameter=([^>]+)>(.*?)</parameter>"
    param_matches = re.findall(param_pattern, xml_content, re.DOTALL)

    arguments: dict[str, Any] = {}
    for param_name, param_value in param_matches:
        arguments[param_name.strip()] = param_value.strip()

    return {"name": func_name, "arguments": arguments}


def _parse_xml_function_block(func_name: str, params_block: str) -> dict[str, Any] | None:
    """Parse XML function block (broken format without <tool_call> opening tag).

    Args:
        func_name: Function name extracted from <function=name>
        params_block: Content between <function> and </function> tags

    Returns:
        Tool call dict with 'name' and 'arguments' keys, or None if parsing fails
    """
    # Extract parameters
    param_pattern = r"<parameter=([^>]+)>(.*?)</parameter>"
    param_matches = re.findall(param_pattern, params_block, re.DOTALL)

    arguments: dict[str, Any] = {}
    for param_name, param_value in param_matches:
        arguments[param_name.strip()] = param_value.strip()

    if not arguments:
        return None

    return {"name": func_name.strip(), "arguments": arguments}
