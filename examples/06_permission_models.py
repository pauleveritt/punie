"""Example 06: Permission Models

Demonstrates permission option types and request construction.

This example shows:
- default_permission_options() factory returning 3-tuple
- Custom PermissionOption construction
- Building ToolCallUpdate for permission request body
- Constructing RequestPermissionRequest with session_id, tool_call, options

Tier: 1 (Sync, schema-only)
"""

from acp import RequestPermissionRequest
from acp.contrib import default_permission_options
from acp.schema import PermissionOption, ToolCallLocation, ToolCallUpdate


def main() -> None:
    """Demonstrate permission request construction patterns."""

    # default_permission_options() returns (approve, approve_for_session, reject)
    approve, approve_session, reject = default_permission_options()
    assert isinstance(approve, PermissionOption)
    assert isinstance(approve_session, PermissionOption)
    assert isinstance(reject, PermissionOption)
    assert approve.name == "Approve"
    assert approve.kind == "allow_once"
    assert approve_session.name == "Approve for session"
    assert approve_session.kind == "allow_always"
    assert reject.name == "Reject"
    assert reject.kind == "reject_once"

    # Custom permission option
    custom_option = PermissionOption(
        option_id="custom-1", name="Approve with logging", kind="allow_once"
    )
    assert custom_option.name == "Approve with logging"
    assert custom_option.kind == "allow_once"

    # Build ToolCallUpdate for permission request body
    tool_call_update = ToolCallUpdate(
        tool_call_id="tool-123",
        title="Editing source",
        kind="edit",
        locations=[ToolCallLocation(path="/path/to/source.py", line=42)],
        raw_input='{"file_path": "/path/to/source.py", "old_string": "old", "new_string": "new"}',
    )
    assert tool_call_update.tool_call_id == "tool-123"
    assert tool_call_update.kind == "edit"

    # Construct full permission request
    permission_request = RequestPermissionRequest(
        session_id="session-456",
        tool_call=tool_call_update,
        options=[approve, approve_session, reject, custom_option],
    )
    assert permission_request.session_id == "session-456"
    assert permission_request.tool_call.tool_call_id == "tool-123"
    assert len(permission_request.options) == 4
    assert permission_request.options[0].name == "Approve"
    assert permission_request.options[3].name == "Approve with logging"

    print("✓ All permission model patterns verified")


if __name__ == "__main__":
    main()
