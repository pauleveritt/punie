"""Tests for execute_code tool integration."""

import pytest
from pydantic_ai import RunContext

from punie.agent.deps import ACPDeps
from punie.agent.monty_runner import ExternalFunctions, run_code
from punie.agent.typed_tools import (
    DocumentSymbolsResult,
    FindReferencesResult,
    GitDiffResult,
    GitLogResult,
    GitStatusResult,
    GotoDefinitionResult,
    HoverResult,
    RuffResult,
    TestResult,
    TypeCheckResult,
    WorkspaceSymbolsResult,
)


def test_execute_code_tool_exists():
    """execute_code tool is available in toolset."""
    from punie.agent.toolset import execute_code

    assert execute_code is not None
    assert callable(execute_code)


def test_execute_code_has_correct_signature():
    """execute_code has correct parameter signature."""
    from inspect import signature

    from punie.agent.toolset import execute_code

    sig = signature(execute_code)
    params = list(sig.parameters.keys())

    assert "ctx" in params
    assert "code" in params
    assert len(params) == 2


def test_execute_code_in_create_toolset():
    """create_toolset includes execute_code."""
    from punie.agent.toolset import create_toolset

    toolset = create_toolset()
    # toolset.tools is a dict mapping tool names to Tool objects
    assert "execute_code" in toolset.tools


def test_execute_code_runs_simple_python():
    """execute_code can run simple Python with fake external functions."""
    # This tests the integration with monty_runner directly

    def fake_read(path: str) -> str:
        return "test content"

    def fake_write(path: str, content: str) -> str:
        return "success"

    def fake_run(command: str, args=None, cwd=None) -> str:
        return "output"

    def fake_typecheck(path: str) -> TypeCheckResult:
        return TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[])

    def fake_ruff(path: str) -> RuffResult:
        return RuffResult(success=True, violation_count=0, fixable_count=0, violations=[])

    def fake_pytest(path: str) -> TestResult:
        return TestResult(success=True, passed=0, failed=0, errors=0, skipped=0, duration=0.0, tests=[])

    def fake_goto_definition(file_path: str, line: int, col: int, symbol: str) -> GotoDefinitionResult:
        return GotoDefinitionResult(success=False, symbol=symbol, locations=[])

    def fake_find_references(file_path: str, line: int, col: int, symbol: str) -> FindReferencesResult:
        return FindReferencesResult(success=False, symbol=symbol, reference_count=0, references=[])

    def fake_hover(file_path: str, line: int, col: int, symbol: str) -> HoverResult:
        return HoverResult(success=False, symbol=symbol)

    def fake_document_symbols(file_path: str) -> DocumentSymbolsResult:
        return DocumentSymbolsResult(success=False, file_path=file_path, symbols=[])

    def fake_workspace_symbols(query: str) -> WorkspaceSymbolsResult:
        return WorkspaceSymbolsResult(success=False, query=query, symbols=[])

    def fake_git_status(path: str) -> GitStatusResult:
        return GitStatusResult(success=True, clean=True, file_count=0, files=[])

    def fake_git_diff(path: str, staged: bool = False) -> GitDiffResult:
        return GitDiffResult(success=True, file_count=0, additions=0, deletions=0, files=[])

    def fake_git_log(path: str, count: int = 10) -> GitLogResult:
        return GitLogResult(success=True, commits=[], commit_count=0)

    external_functions = ExternalFunctions(
        fake_read, fake_write, fake_run, fake_typecheck, fake_ruff, fake_pytest,
        fake_goto_definition, fake_find_references, fake_hover, fake_document_symbols,
        fake_workspace_symbols, fake_git_status, fake_git_diff, fake_git_log
    )

    code = """
content = read_file("test.txt")
print(f"Read: {content}")
"""

    result = run_code(code, external_functions)
    assert "Read: test content" in result


def test_execute_code_docstring_mentions_code_mode():
    """execute_code docstring documents Code Mode."""
    from punie.agent.toolset import execute_code

    doc = execute_code.__doc__
    assert "Code Mode" in doc
    assert "multi-step" in doc


async def test_execute_code_tracks_lifecycle_structure():
    """execute_code has proper lifecycle tracking structure (start/progress/forget)."""
    from inspect import getsource

    from punie.agent.toolset import execute_code

    source = getsource(execute_code)

    # Verify lifecycle tracking is present in structure
    assert "tracker.start" in source
    assert "tracker.progress" in source
    assert "tracker.forget" in source
    assert "session_update" in source


async def test_execute_code_async_bridge_integration():
    """execute_code async bridge properly calls async ACP functions from sync sandbox."""
    from unittest.mock import AsyncMock, MagicMock, Mock

    from punie.acp.schema import (
        CreateTerminalResponse,
        ReadTextFileResponse,
        TerminalOutputResponse,
    )
    from punie.agent.toolset import execute_code

    # Create mock ACP client with async methods
    mock_client = AsyncMock()
    mock_client.read_text_file = AsyncMock(
        return_value=ReadTextFileResponse(content="file content from ACP")
    )
    mock_client.write_text_file = AsyncMock(return_value=None)

    # Mock terminal workflow (create -> wait -> output -> release)
    mock_client.create_terminal = AsyncMock(
        return_value=CreateTerminalResponse(terminal_id="term-123")
    )
    mock_client.wait_for_terminal_exit = AsyncMock(return_value=MagicMock())
    mock_client.terminal_output = AsyncMock(
        return_value=TerminalOutputResponse(output="command output", truncated=False)
    )
    mock_client.release_terminal = AsyncMock(return_value=None)

    mock_client.session_update = AsyncMock(return_value=None)

    # Create mock tracker (returns dict-like objects)
    mock_tracker = Mock()
    mock_tracker.start = Mock(return_value=MagicMock())
    mock_tracker.progress = Mock(return_value=MagicMock())
    mock_tracker.forget = Mock(return_value=MagicMock())

    # Create context with mocked dependencies
    deps = ACPDeps(
        client_conn=mock_client,
        session_id="test-session",
        tracker=mock_tracker,
    )
    ctx = RunContext(
        deps=deps,
        retry=0,
        tool_name="execute_code",
        model=MagicMock(),
        usage=MagicMock(),
    )

    # Test code that calls all three external functions
    code = """
# Read a file
content = read_file("test.txt")
print(f"Read: {content}")

# Write a file
write_file("output.txt", "new content")
print("Wrote file")

# Run a command
result = run_command("ls", ["-la"], "/tmp")
print(f"Command: {result}")
"""

    # Execute code (should use async bridge internally)
    result = await execute_code(ctx, code)

    # Verify async ACP methods were called through the bridge
    mock_client.read_text_file.assert_called_once_with(
        session_id="test-session", path="test.txt"
    )
    mock_client.write_text_file.assert_called_once_with(
        session_id="test-session", path="output.txt", content="new content"
    )

    # Verify terminal workflow was used for run_command
    mock_client.create_terminal.assert_called_once_with(
        command="ls", args=["-la"], cwd="/tmp", session_id="test-session"
    )
    mock_client.wait_for_terminal_exit.assert_called_once_with(
        session_id="test-session", terminal_id="term-123"
    )
    mock_client.terminal_output.assert_called_once_with(
        session_id="test-session", terminal_id="term-123"
    )
    mock_client.release_terminal.assert_called_once_with(
        session_id="test-session", terminal_id="term-123"
    )

    # Verify result contains output from all operations
    assert "Read: file content from ACP" in result
    assert "Wrote file" in result
    assert "Command: command output" in result
