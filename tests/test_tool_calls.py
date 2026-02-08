"""ACP tool call lifecycle tests.

Tests for tool call flow including permissions and status tracking.
"""

import asyncio

import pytest

from punie.acp import start_tool_call, update_tool_call
from punie.acp.schema import PermissionOption, ToolCallLocation, ToolCallUpdate


@pytest.mark.thread_unsafe
async def test_tool_call_lifecycle(connect, client):
    """Test 6: Full tool call flow with permission and status tracking.

    Proves tool call lifecycle works: start → permission → update → complete.
    This is critical for Punie's PyCharm integration.
    """
    # Queue permission response
    client.queue_permission_selected("allow")

    client_conn, _ = connect()

    # Start tool call
    await client_conn.session_update(
        session_id="sess",
        update=start_tool_call(
            "call_1",
            "Modifying file",
            kind="edit",
            status="pending",
            locations=[ToolCallLocation(path="/project/file.py")],
            raw_input={"path": "/project/file.py"},
        ),
    )

    # Request permission
    permission_response = await client_conn.request_permission(
        session_id="sess",
        tool_call=ToolCallUpdate(
            tool_call_id="call_1",
            title="Modifying file",
            kind="edit",
            status="pending",
            locations=[ToolCallLocation(path="/project/file.py")],
            raw_input={"path": "/project/file.py"},
        ),
        options=[
            PermissionOption(kind="allow_once", name="Allow", option_id="allow"),
            PermissionOption(kind="reject_once", name="Reject", option_id="reject"),
        ],
    )

    # Check permission granted
    assert permission_response.outcome.outcome == "selected"

    # Update tool call to completed
    await client_conn.session_update(
        session_id="sess",
        update=update_tool_call(
            "call_1",
            status="completed",
            raw_output={"success": True},
        ),
    )

    # Wait for notifications
    for _ in range(50):
        if len(client.notifications) >= 2:
            break
        await asyncio.sleep(0.01)

    # Verify tool call updates received
    assert len(client.notifications) >= 2
