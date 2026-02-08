"""Example 03: Tool Call Models

Demonstrates tool call lifecycle models and factory functions.

This example shows:
- start_tool_call() with kind, status, locations, raw_input
- Convenience factories: start_read_tool_call(), start_edit_tool_call()
- update_tool_call() to transition tool call status
- tool_diff_content() for file edit diffs
- Tool call IDs, status transitions, and location tracking

Tier: 1 (Sync, schema-only)
"""

from punie.acp import (
    start_edit_tool_call,
    start_read_tool_call,
    start_tool_call,
    tool_diff_content,
    update_tool_call,
)
from punie.acp.schema import ToolCallLocation


def main() -> None:
    """Demonstrate tool call lifecycle model construction."""

    # start_tool_call() with explicit parameters
    location = ToolCallLocation(path="/path/to/file.py", line=42)
    tool_call_start = start_tool_call(
        "call-1",
        "Reading file",
        kind="read",
        status="in_progress",
        locations=[location],
        raw_input='{"file_path": "/path/to/file.py"}',
    )
    assert tool_call_start.tool_call_id == "call-1"
    assert tool_call_start.title == "Reading file"
    assert tool_call_start.kind == "read"
    assert tool_call_start.status == "in_progress"
    assert tool_call_start.locations is not None
    assert len(tool_call_start.locations) == 1
    assert tool_call_start.locations[0].path == "/path/to/file.py"
    assert tool_call_start.raw_input == '{"file_path": "/path/to/file.py"}'
    tool_call_id = tool_call_start.tool_call_id

    # Convenience factory: start_read_tool_call()
    read_call = start_read_tool_call("call-2", "Reading readme", "/path/to/readme.md")
    assert read_call.kind == "read"
    assert read_call.status == "pending"
    assert read_call.locations is not None
    assert len(read_call.locations) == 1
    assert read_call.locations[0].path == "/path/to/readme.md"

    # Convenience factory: start_edit_tool_call()
    edit_call = start_edit_tool_call(
        "call-3",
        "Editing source",
        "/path/to/source.py",
        {"old_string": "old", "new_string": "new"},
    )
    assert edit_call.kind == "edit"
    assert edit_call.status == "pending"
    assert edit_call.locations is not None
    assert edit_call.locations[0].path == "/path/to/source.py"

    # update_tool_call() to transition status
    progress_update = update_tool_call(tool_call_id, status="completed")
    assert progress_update.tool_call_id == tool_call_id
    assert progress_update.status == "completed"

    # tool_diff_content() for edit diffs
    diff_block = tool_diff_content(
        path="/path/to/edited.py", new_text="new line", old_text="old line"
    )
    assert diff_block.type == "diff"
    assert diff_block.path == "/path/to/edited.py"
    assert diff_block.old_text == "old line"
    assert diff_block.new_text == "new line"

    print("✓ All tool call model patterns verified")


if __name__ == "__main__":
    main()
