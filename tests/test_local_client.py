"""Tests for LocalClient with real filesystem and subprocess operations."""

from pathlib import Path

import pytest

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.acp.interfaces import Client
from punie.acp.schema import (
    AllowedOutcome,
    PermissionOption,
    ToolCallUpdate,
)
from punie.agent.deps import ACPDeps
from punie.agent.factory import create_local_agent
from punie.local import LocalClient


def test_local_client_satisfies_client_protocol():
    """LocalClient satisfies Client protocol (first test per standard)."""
    client = LocalClient(workspace=Path.cwd())
    assert isinstance(client, Client)


async def test_read_text_file_returns_content(tmp_path: Path):
    """Read file from local filesystem."""
    client = LocalClient(workspace=tmp_path)

    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    # Read via client
    response = await client.read_text_file(
        path="test.txt",
        session_id="test-session",
    )

    assert response.content == "hello world"


async def test_read_text_file_missing_file(tmp_path: Path):
    """Read missing file raises appropriate error."""
    client = LocalClient(workspace=tmp_path)

    with pytest.raises(FileNotFoundError):
        await client.read_text_file(
            path="missing.txt",
            session_id="test-session",
        )


async def test_read_text_file_with_line_and_limit(tmp_path: Path):
    """Read file with line and limit parameters."""
    client = LocalClient(workspace=tmp_path)

    # Create multi-line test file
    test_file = tmp_path / "lines.txt"
    test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

    # Read lines 2-3 (line is 1-indexed)
    response = await client.read_text_file(
        path="lines.txt",
        session_id="test-session",
        line=2,
        limit=2,
    )

    assert response.content == "line2\nline3\n"


async def test_write_text_file_creates_file(tmp_path: Path):
    """Write file to local filesystem."""
    client = LocalClient(workspace=tmp_path)

    response = await client.write_text_file(
        content="test content",
        path="new.txt",
        session_id="test-session",
    )

    assert response is not None
    assert (tmp_path / "new.txt").read_text() == "test content"


async def test_write_text_file_overwrites(tmp_path: Path):
    """Write file overwrites existing file."""
    client = LocalClient(workspace=tmp_path)

    # Create initial file
    test_file = tmp_path / "existing.txt"
    test_file.write_text("old content")

    # Overwrite via client
    await client.write_text_file(
        content="new content",
        path="existing.txt",
        session_id="test-session",
    )

    assert test_file.read_text() == "new content"


async def test_write_text_file_creates_parent_dirs(tmp_path: Path):
    """Write file creates parent directories."""
    client = LocalClient(workspace=tmp_path)

    await client.write_text_file(
        content="nested content",
        path="subdir/nested/file.txt",
        session_id="test-session",
    )

    assert (tmp_path / "subdir" / "nested" / "file.txt").read_text() == "nested content"


async def test_request_permission_auto_approves(tmp_path: Path):
    """Auto-approve permission by selecting first option."""
    client = LocalClient(workspace=tmp_path)

    options = [
        PermissionOption(kind="allow_once", name="Option 1", option_id="opt1"),
        PermissionOption(kind="allow_once", name="Option 2", option_id="opt2"),
    ]

    response = await client.request_permission(
        options=options,
        session_id="test-session",
        tool_call=ToolCallUpdate(tool_call_id="tc1"),
    )

    assert isinstance(response.outcome, AllowedOutcome)
    assert response.outcome.option_id == "opt1"


async def test_request_permission_empty_options(tmp_path: Path):
    """Auto-approve with empty options."""
    client = LocalClient(workspace=tmp_path)

    response = await client.request_permission(
        options=[],
        session_id="test-session",
        tool_call=ToolCallUpdate(tool_call_id="tc1"),
    )

    assert isinstance(response.outcome, AllowedOutcome)
    assert response.outcome.option_id == ""


async def test_session_update_no_op(tmp_path: Path):
    """Session update is a no-op (no IDE to receive)."""
    from punie.acp.schema import TextContentBlock, UserMessageChunk

    client = LocalClient(workspace=tmp_path)

    # Should not raise
    await client.session_update(
        session_id="test-session",
        update=UserMessageChunk(
            content=TextContentBlock(text="test", type="text"),
            session_update="user_message_chunk",
        ),
    )


async def test_create_terminal_runs_command(tmp_path: Path):
    """Create subprocess for command execution."""
    client = LocalClient(workspace=tmp_path)

    response = await client.create_terminal(
        command="echo",
        args=["hello"],
        session_id="test-session",
    )

    assert response.terminal_id.startswith("term-")
    assert response.terminal_id in client._terminals


async def test_terminal_output_returns_stdout(tmp_path: Path):
    """Capture subprocess output."""
    client = LocalClient(workspace=tmp_path)

    # Create terminal
    response = await client.create_terminal(
        command="echo",
        args=["hello world"],
        session_id="test-session",
    )
    terminal_id = response.terminal_id

    # Wait for process to complete
    await client.wait_for_terminal_exit(
        session_id="test-session",
        terminal_id=terminal_id,
    )

    # Get output
    output_response = await client.terminal_output(
        session_id="test-session",
        terminal_id=terminal_id,
    )

    assert "hello world" in output_response.output


async def test_wait_for_terminal_exit_returns_code(tmp_path: Path):
    """Wait for subprocess to complete and return exit code."""
    client = LocalClient(workspace=tmp_path)

    # Create terminal with successful command
    response = await client.create_terminal(
        command="echo",
        args=["test"],
        session_id="test-session",
    )
    terminal_id = response.terminal_id

    # Wait for exit
    exit_response = await client.wait_for_terminal_exit(
        session_id="test-session",
        terminal_id=terminal_id,
    )

    assert exit_response.exit_code == 0


async def test_kill_terminal_stops_process(tmp_path: Path):
    """Kill a running process."""
    client = LocalClient(workspace=tmp_path)

    # Create terminal with long-running command
    response = await client.create_terminal(
        command="sleep",
        args=["10"],
        session_id="test-session",
    )
    terminal_id = response.terminal_id

    # Kill it
    kill_response = await client.kill_terminal(
        session_id="test-session",
        terminal_id=terminal_id,
    )

    assert kill_response is not None
    assert terminal_id not in client._terminals


async def test_release_terminal_cleans_up(tmp_path: Path):
    """Release terminal removes reference."""
    client = LocalClient(workspace=tmp_path)

    # Create and complete terminal
    response = await client.create_terminal(
        command="echo",
        args=["test"],
        session_id="test-session",
    )
    terminal_id = response.terminal_id

    await client.wait_for_terminal_exit(
        session_id="test-session",
        terminal_id=terminal_id,
    )

    # Release terminal
    release_response = await client.release_terminal(
        session_id="test-session",
        terminal_id=terminal_id,
    )

    assert release_response is not None
    assert terminal_id not in client._terminals


async def test_terminal_not_found_raises(tmp_path: Path):
    """Terminal operations with invalid ID raise KeyError."""
    client = LocalClient(workspace=tmp_path)

    with pytest.raises(KeyError, match="Terminal.*not found"):
        await client.terminal_output(
            session_id="test-session",
            terminal_id="invalid-id",
        )

    with pytest.raises(KeyError, match="Terminal.*not found"):
        await client.wait_for_terminal_exit(
            session_id="test-session",
            terminal_id="invalid-id",
        )

    with pytest.raises(KeyError, match="Terminal.*not found"):
        await client.kill_terminal(
            session_id="test-session",
            terminal_id="invalid-id",
        )


async def test_discover_tools_returns_empty(tmp_path: Path):
    """No IDE discovery in local mode."""
    client = LocalClient(workspace=tmp_path)

    result = await client.discover_tools(session_id="test-session")

    assert result == {"tools": []}


async def test_ext_method_raises(tmp_path: Path):
    """Extension methods not supported in local mode."""
    client = LocalClient(workspace=tmp_path)

    with pytest.raises(NotImplementedError, match="not supported in local mode"):
        await client.ext_method("test.method", {})


async def test_ext_notification_no_op(tmp_path: Path):
    """Extension notifications are no-op."""
    client = LocalClient(workspace=tmp_path)

    # Should not raise
    await client.ext_notification("test.notification", {})


def test_on_connect_stores_agent(tmp_path: Path):
    """on_connect stores agent reference."""
    client = LocalClient(workspace=tmp_path)

    mock_agent = object()
    client.on_connect(mock_agent)

    assert client._agent is mock_agent


async def test_existing_tools_work_with_local_client(tmp_path: Path):
    """Verify ACPDeps and LocalClient work together."""
    client = LocalClient(workspace=tmp_path)
    tracker = ToolCallTracker()

    # Create test file
    test_file = tmp_path / "tool_test.txt"
    test_file.write_text("tool content")

    # Create deps
    deps = ACPDeps(
        client_conn=client,
        session_id="test-session",
        tracker=tracker,
    )

    # Verify deps work with LocalClient
    response = await deps.client_conn.read_text_file(
        path="tool_test.txt",
        session_id=deps.session_id,
    )

    assert "tool content" in response.content


async def test_tracker_lifecycle_with_local_client(tmp_path: Path):
    """ToolCallTracker works with LocalClient (session_update is no-op)."""
    from punie.acp.schema import ContentToolCallContent, TextContentBlock

    client = LocalClient(workspace=tmp_path)
    tracker = ToolCallTracker()

    # Start tracking
    tool_call_start = tracker.start(external_id="tc1", title="test_tool")

    # Simulate session update (should not raise)
    await client.session_update(
        session_id="test-session",
        update=tool_call_start,
    )

    # Update with progress using correct content type
    progress_update = tracker.progress(
        external_id="tc1",
        status="completed",
        content=[
            ContentToolCallContent(
                content=TextContentBlock(text="result", type="text"),
                type="content",
            )
        ],
    )

    # Simulate progress update (should not raise)
    await client.session_update(
        session_id="test-session",
        update=progress_update,
    )

    # Verify tracker can view the call
    view = tracker.view(external_id="tc1")
    assert view.title == "test_tool"
    assert view.status == "completed"


def test_create_local_agent_factory():
    """create_local_agent factory creates agent with LocalClient."""
    agent, client = create_local_agent(model="test")

    assert isinstance(client, LocalClient)
    assert client.workspace == Path.cwd()


def test_create_local_agent_with_workspace(tmp_path: Path):
    """create_local_agent with custom workspace."""
    agent, client = create_local_agent(model="test", workspace=tmp_path)

    assert isinstance(client, LocalClient)
    assert client.workspace == tmp_path
