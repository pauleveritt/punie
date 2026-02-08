"""Example 05: Tool Call Tracker

Demonstrates agent-side tool call state management with ToolCallTracker.

This example shows:
- Creating ToolCallTracker with deterministic id_factory
- tracker.start() to create ToolCallStart
- tracker.view() to get immutable TrackedToolCallView
- tracker.tool_call_model() to create ToolCallUpdate for permission requests
- tracker.progress() to update tool call status
- tracker.forget() to clean up completed tool calls

Tier: 1 (Sync, schema-only)
"""

from acp.contrib import ToolCallTracker
from acp.schema import ToolCallLocation


def main() -> None:
    """Demonstrate tool call tracking lifecycle."""

    # Create tracker with deterministic ID factory
    counter = 0

    def id_factory() -> str:
        nonlocal counter
        counter += 1
        return f"tool-{counter}"

    tracker = ToolCallTracker(id_factory=id_factory)

    # Start a tool call
    location = ToolCallLocation(path="/path/to/file.py", line=10)
    start_notification = tracker.start(
        "ext-1",
        title="Reading file",
        kind="read",
        locations=[location],
        raw_input='{"file_path": "/path/to/file.py"}',
    )
    assert start_notification.tool_call_id == "tool-1"
    assert start_notification.kind == "read"
    assert start_notification.status == "in_progress"

    # Get immutable view
    view = tracker.view("ext-1")
    assert view.tool_call_id == "tool-1"
    assert view.kind == "read"
    assert view.status == "in_progress"
    assert len(view.locations) == 1

    # Create ToolCallUpdate for permission request
    tool_call_model = tracker.tool_call_model("ext-1")
    assert tool_call_model.tool_call_id == "tool-1"
    assert tool_call_model.kind == "read"

    # Update status to completed
    progress_notification = tracker.progress("ext-1", status="completed")
    assert progress_notification.tool_call_id == "tool-1"
    assert progress_notification.status == "completed"

    # Verify view reflects update
    updated_view = tracker.view("ext-1")
    assert updated_view.status == "completed"

    # Clean up
    tracker.forget("ext-1")

    # Verify tool call is gone (should raise KeyError)
    try:
        tracker.view("ext-1")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass  # Expected

    print("✓ All tool call tracker patterns verified")


if __name__ == "__main__":
    main()
