"""Workspace boundary enforcement for local file operations.

Prevents LocalClient from accessing files outside the workspace directory
through path traversal attacks (e.g., ../../etc/passwd) or symlink escapes.
"""

from pathlib import Path


class WorkspaceBoundaryError(Exception):
    """Raised when a path resolves outside the workspace directory.

    Attributes:
        path: The attempted path that violated the boundary
        workspace: The workspace root directory
    """

    def __init__(self, path: Path, workspace: Path):
        self.path = path
        self.workspace = workspace
        super().__init__(f"Path {path} is outside workspace {workspace}")


def resolve_workspace_path(workspace: Path, path: str) -> Path:
    """Resolve path ensuring it stays within workspace boundary.

    Algorithm:
    1. Join workspace + path
    2. Call .resolve() to canonicalize (handles symlinks, .., etc.)
    3. Check resolved.is_relative_to(workspace.resolve())
    4. Raise WorkspaceBoundaryError if outside

    Args:
        workspace: Root workspace directory (must exist)
        path: File path to resolve (relative or absolute)

    Returns:
        Resolved absolute path within workspace

    Raises:
        WorkspaceBoundaryError: If resolved path is outside workspace

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     workspace = Path(tmpdir)
        ...     result = resolve_workspace_path(workspace, "src/main.py")
        ...     result.parent.name
        'src'

        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     workspace = Path(tmpdir)
        ...     try:
        ...         resolve_workspace_path(workspace, "../../../etc/passwd")
        ...     except WorkspaceBoundaryError as e:
        ...         print("WorkspaceBoundaryError raised")
        WorkspaceBoundaryError raised
    """
    # Join workspace + path and canonicalize
    full_path = (workspace / path).resolve()
    workspace_resolved = workspace.resolve()

    # Check if resolved path is within workspace
    if not full_path.is_relative_to(workspace_resolved):
        raise WorkspaceBoundaryError(full_path, workspace_resolved)

    return full_path
