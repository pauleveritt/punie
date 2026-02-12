"""Tests for tool call parsing utilities.

Tests verify that parse_tool_calls() correctly extracts tool calls from model
output in both JSON and XML formats, including edge cases like broken XML.
"""

from punie.training.tool_call_parser import parse_tool_calls


def test_parse_single_json_tool_call():
    """Parse a single JSON-format tool call from model output."""
    text = 'Some text<tool_call>{"name": "read_file", "arguments": {"path": "foo.py"}}</tool_call>'
    content, calls = parse_tool_calls(text)

    assert content == "Some text"
    assert len(calls) == 1
    assert calls[0]["name"] == "read_file"
    assert calls[0]["arguments"] == {"path": "foo.py"}


def test_parse_multiple_json_tool_calls():
    """Parse multiple JSON-format tool calls from model output."""
    text = (
        'Let me help<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>'
        ' and <tool_call>{"name": "write_file", "arguments": {"path": "b.py", "content": "x"}}</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Let me help and"
    assert len(calls) == 2
    assert calls[0]["name"] == "read_file"
    assert calls[1]["name"] == "write_file"


def test_parse_xml_tool_call():
    """Parse XML-format tool call with parameters."""
    text = (
        'Let me list files<tool_call>'
        '<function=list_files>'
        '<parameter=path>.</parameter>'
        '<parameter=pattern>*.py</parameter>'
        '</function>'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Let me list files"
    assert len(calls) == 1
    assert calls[0]["name"] == "list_files"
    assert calls[0]["arguments"] == {"path": ".", "pattern": "*.py"}


def test_parse_xml_tool_call_single_parameter():
    """Parse XML-format tool call with single parameter."""
    text = (
        'Reading<tool_call>'
        '<function=read_file>'
        '<parameter=path>/path/to/file.py</parameter>'
        '</function>'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Reading"
    assert len(calls) == 1
    assert calls[0]["name"] == "read_file"
    assert calls[0]["arguments"] == {"path": "/path/to/file.py"}


def test_parse_broken_xml_missing_opening_tag():
    """Parse broken XML format missing opening <tool_call> tag."""
    text = (
        'Let me search'
        '<function=search_code>'
        '<parameter=query>def main</parameter>'
        '<parameter=file_pattern>*.py</parameter>'
        '</function></tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Let me search"
    assert len(calls) == 1
    assert calls[0]["name"] == "search_code"
    assert calls[0]["arguments"] == {"query": "def main", "file_pattern": "*.py"}


def test_parse_no_tool_calls():
    """Parse text with no tool calls returns empty list."""
    text = "Just plain text with no tool calls."
    content, calls = parse_tool_calls(text)

    assert content == "Just plain text with no tool calls."
    assert calls == []


def test_parse_invalid_json_tool_call():
    """Invalid JSON in tool call is stripped but not added to calls."""
    text = 'Text<tool_call>{"name": "read", invalid json}</tool_call> more text'
    content, calls = parse_tool_calls(text)

    # Invalid JSON should be stripped but not added to calls
    assert "invalid json" not in content
    assert "<tool_call>" not in content
    assert content == "Text more text"
    assert calls == []


def test_parse_json_tool_call_missing_name():
    """Tool call without 'name' field is skipped."""
    text = 'Text<tool_call>{"arguments": {"path": "foo.py"}}</tool_call>'
    content, calls = parse_tool_calls(text)

    # Missing name means invalid tool call - should be stripped
    assert calls == []
    assert "<tool_call>" not in content


def test_parse_xml_tool_call_missing_function_tag():
    """XML tool call without function tag is skipped."""
    text = 'Text<tool_call><parameter=path>.</parameter></tool_call>'
    content, calls = parse_tool_calls(text)

    # Missing function tag means invalid - should be stripped
    assert calls == []
    assert "<tool_call>" not in content


def test_parse_mixed_text_and_tool_calls():
    """Parse text with interleaved content and multiple tool calls."""
    text = (
        'First, I will read the file '
        '<tool_call>{"name": "read_file", "arguments": {"path": "main.py"}}</tool_call> '
        'and then I will search for the function '
        '<tool_call>{"name": "search_code", "arguments": {"query": "def process"}}</tool_call> '
        'to understand the logic.'
    )
    content, calls = parse_tool_calls(text)

    assert "First, I will read the file" in content
    assert "and then I will search for the function" in content
    assert "to understand the logic." in content
    assert len(calls) == 2
    assert calls[0]["name"] == "read_file"
    assert calls[1]["name"] == "search_code"


def test_parse_tool_call_preserves_whitespace():
    """Tool call parsing preserves meaningful whitespace in remaining text."""
    text = (
        'Line 1\n'
        '<tool_call>{"name": "test", "arguments": {}}</tool_call>\n'
        'Line 2'
    )
    content, calls = parse_tool_calls(text)

    # Should preserve the newline structure (but strip() at end removes trailing/leading)
    assert "Line 1" in content
    assert "Line 2" in content
    assert len(calls) == 1


def test_parse_xml_with_multiline_parameter_values():
    """Parse XML tool call with multiline parameter values."""
    text = (
        '<tool_call>'
        '<function=write_file>'
        '<parameter=path>test.py</parameter>'
        '<parameter=content>line 1\nline 2\nline 3</parameter>'
        '</function>'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert len(calls) == 1
    assert calls[0]["name"] == "write_file"
    assert calls[0]["arguments"]["content"] == "line 1\nline 2\nline 3"


def test_parse_empty_string():
    """Parse empty string returns empty results."""
    content, calls = parse_tool_calls("")

    assert content == ""
    assert calls == []


def test_parse_tool_call_with_nested_json():
    """Parse tool call with nested JSON in arguments."""
    text = (
        '<tool_call>'
        '{"name": "update_config", "arguments": {"config": {"key1": "value1", "key2": {"nested": true}}}}'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == ""
    assert len(calls) == 1
    assert calls[0]["name"] == "update_config"
    assert calls[0]["arguments"]["config"]["key2"]["nested"] is True
