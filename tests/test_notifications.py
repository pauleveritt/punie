"""ACP notification tests.

Tests for one-way and bidirectional notifications.
"""

import asyncio

import pytest

from punie.acp.schema import AgentMessageChunk, TextContentBlock, UserMessageChunk


@pytest.mark.thread_unsafe
async def test_cancel_notification_dispatched(connect, agent):
    """Test 4: One-way notification from client to agent.

    Proves cancel notification propagates correctly to agent handler.
    """
    _, agent_conn = connect()

    # Send cancel notification
    await agent_conn.cancel(session_id="test-123")

    # Wait for async dispatch
    for _ in range(50):
        if agent.cancellations:
            break
        await asyncio.sleep(0.01)

    assert agent.cancellations == ["test-123"]


@pytest.mark.thread_unsafe
async def test_session_update_notifications(connect, client):
    """Test 5: Agent-to-client notifications via session_update.

    Proves message notifications dispatch correctly from agent to client.
    """
    client_conn, _ = connect()

    # Send agent message notification
    await client_conn.session_update(
        session_id="sess",
        update=AgentMessageChunk(
            session_update="agent_message_chunk",
            content=TextContentBlock(type="text", text="Hello"),
        ),
    )

    # Send user message notification
    await client_conn.session_update(
        session_id="sess",
        update=UserMessageChunk(
            session_update="user_message_chunk",
            content=TextContentBlock(type="text", text="World"),
        ),
    )

    # Wait for async dispatch
    for _ in range(50):
        if len(client.notifications) >= 2:
            break
        await asyncio.sleep(0.01)

    assert len(client.notifications) >= 2
    assert client.notifications[0].session_id == "sess"
    assert isinstance(client.notifications[0].update, AgentMessageChunk)
    assert isinstance(client.notifications[1].update, UserMessageChunk)
