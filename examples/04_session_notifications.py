"""Example 04: Session Notifications

Demonstrates session notifications, plan management, and SessionAccumulator.

This example shows:
- Building PlanEntry objects with plan_entry()
- Creating plan updates with update_plan()
- Wrapping updates in session_notification()
- Using SessionAccumulator to aggregate session state
- Taking snapshots to inspect accumulated messages, plan, tool calls

Tier: 1 (Sync, schema-only)
"""

from punie.acp import (
    plan_entry,
    session_notification,
    start_tool_call,
    update_agent_message_text,
    update_plan,
)
from punie.acp.contrib import SessionAccumulator
from punie.acp.schema import ToolCallLocation


def main() -> None:
    """Demonstrate session notification and accumulator patterns."""

    # Create SessionAccumulator
    accumulator = SessionAccumulator()

    # Build a plan entry
    entry = plan_entry(
        content="Read configuration from settings.json",
        status="pending",
        priority="medium",
    )
    assert entry.content == "Read configuration from settings.json"
    assert entry.status == "pending"
    assert entry.priority == "medium"

    # Session ID for notifications
    session_id = "test-session"

    # Create a plan update notification
    plan_update_notif = session_notification(session_id, update_plan(entries=[entry]))
    assert plan_update_notif.session_id == session_id

    # Feed into accumulator
    accumulator.apply(plan_update_notif)

    # Add agent message
    agent_msg = session_notification(
        session_id, update_agent_message_text("Starting configuration read")
    )
    assert agent_msg.session_id == session_id
    accumulator.apply(agent_msg)

    # Add tool call
    tool_call_notif = session_notification(
        session_id,
        start_tool_call(
            "call-1",
            "Reading settings",
            kind="read",
            status="in_progress",
            locations=[ToolCallLocation(path="settings.json")],
            raw_input='{"file_path": "settings.json"}',
        ),
    )
    assert tool_call_notif.session_id == session_id
    accumulator.apply(tool_call_notif)

    # Take snapshot and verify aggregated state
    snapshot = accumulator.snapshot()
    assert len(snapshot.plan_entries) == 1
    assert snapshot.plan_entries[0].content == "Read configuration from settings.json"
    assert len(snapshot.agent_messages) == 1
    assert snapshot.agent_messages[0].content.text == "Starting configuration read"
    assert len(snapshot.tool_calls) == 1
    assert "call-1" in snapshot.tool_calls
    assert snapshot.tool_calls["call-1"].kind == "read"

    print("✓ All session notification patterns verified")


if __name__ == "__main__":
    main()
