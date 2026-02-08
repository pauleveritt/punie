"""Tests for workspace boundary enforcement."""

import tempfile
from pathlib import Path

import pytest

from punie.local import LocalClient, WorkspaceBoundaryError, resolve_workspace_path


def test_resolve_workspace_path_relative():
    """Normal relative paths should be allowed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        result = resolve_workspace_path(workspace, "src/main.py")
        assert result == (workspace / "src" / "main.py").resolve()


def test_resolve_workspace_path_nested():
    """Nested subdirectory paths should be allowed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        result = resolve_workspace_path(workspace, "a/b/c/file.txt")
        assert result == (workspace / "a" / "b" / "c" / "file.txt").resolve()


def test_resolve_workspace_path_traversal_blocked():
    """Path traversal attempts should be blocked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        with pytest.raises(WorkspaceBoundaryError) as exc_info:
            resolve_workspace_path(workspace, "../../etc/passwd")

        # Check that error was raised (path will vary based on tmpdir location)
        assert exc_info.value.workspace == workspace.resolve()
        # Path should be outside workspace
        assert not exc_info.value.path.is_relative_to(workspace.resolve())


def test_resolve_workspace_path_absolute_outside_blocked():
    """Absolute paths outside workspace should be blocked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        with pytest.raises(WorkspaceBoundaryError):
            resolve_workspace_path(workspace, "/etc/passwd")


def test_resolve_workspace_path_absolute_inside_allowed():
    """Absolute paths within workspace should be allowed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        # Create a file in workspace
        test_file = workspace / "test.txt"
        test_file.write_text("content")

        # Resolve using absolute path
        result = resolve_workspace_path(workspace, str(test_file))
        assert result == test_file.resolve()


def test_resolve_workspace_path_symlink_escape_blocked():
    """Symlinks pointing outside workspace should be blocked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        # Create symlink pointing outside
        link = workspace / "escape_link"
        link.symlink_to("/etc/passwd")

        with pytest.raises(WorkspaceBoundaryError):
            resolve_workspace_path(workspace, "escape_link")


def test_resolve_workspace_path_dot_components():
    """Paths with dot components should resolve correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        result = resolve_workspace_path(workspace, "./foo/../bar")
        assert result == (workspace / "bar").resolve()


@pytest.mark.asyncio
async def test_local_client_read_blocked_outside_workspace():
    """LocalClient read_text_file should block paths outside workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        client = LocalClient(workspace=workspace)

        with pytest.raises(WorkspaceBoundaryError):
            await client.read_text_file("/etc/passwd", session_id="test")


@pytest.mark.asyncio
async def test_local_client_write_blocked_outside_workspace():
    """LocalClient write_text_file should block paths outside workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        client = LocalClient(workspace=workspace)

        with pytest.raises(WorkspaceBoundaryError):
            await client.write_text_file("content", "/tmp/evil.txt", session_id="test")


@pytest.mark.asyncio
async def test_local_client_terminal_cwd_blocked_outside_workspace():
    """LocalClient create_terminal should block cwd outside workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        client = LocalClient(workspace=workspace)

        with pytest.raises(WorkspaceBoundaryError):
            await client.create_terminal("ls", session_id="test", cwd="/tmp")


@pytest.mark.asyncio
async def test_local_client_operations_allowed_inside_workspace():
    """LocalClient operations should work inside workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        client = LocalClient(workspace=workspace)

        # Write file
        await client.write_text_file("test content", "test.txt", session_id="test")

        # Read file back
        response = await client.read_text_file("test.txt", session_id="test")
        assert response.content == "test content"

        # Verify file exists in workspace
        assert (workspace / "test.txt").exists()
