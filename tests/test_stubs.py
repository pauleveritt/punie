"""Tests for function stub generation and command splitting for sandbox toolset.

Consolidates:
- Stub generation (generate_stubs, get_stub_instructions)
- Command splitting logic for run_command (shlex.split usage)
"""

from __future__ import annotations

import shlex

from punie.agent.stubs import generate_stubs, get_stub_instructions


# ============================================================================
# Stub Generation Tests
# ============================================================================


def test_generate_stubs_includes_all_core_functions():
    """Stubs include all three core functions from toolset."""
    stubs = generate_stubs()

    assert "def read_file(path: str) -> str:" in stubs
    assert "def write_file(path: str, content: str) -> str:" in stubs
    assert "def run_command(command: str" in stubs


def test_stubs_exclude_ctx_parameter():
    """Generated stubs don't include RunContext parameter."""
    stubs = generate_stubs()

    assert "RunContext" not in stubs
    assert "ACPDeps" not in stubs
    assert "ctx:" not in stubs


def test_stubs_include_docstrings():
    """Generated stubs include first line of docstrings."""
    stubs = generate_stubs()

    assert "Read contents of a text file" in stubs
    assert "Write contents to a text file" in stubs
    assert "Run a shell command" in stubs


def test_stubs_include_optional_parameters():
    """Generated stubs preserve optional parameters with defaults."""
    stubs = generate_stubs()

    # run_command has optional args and cwd parameters
    assert "args:" in stubs
    assert "cwd:" in stubs
    assert "None" in stubs


def test_get_stub_instructions_includes_constraints():
    """Instructions document code mode constraints."""
    instructions = get_stub_instructions()

    assert "No classes allowed" in instructions
    assert "Limited stdlib" in instructions
    assert "execute_code" in instructions


def test_get_stub_instructions_includes_example():
    """Instructions include a complete example."""
    instructions = get_stub_instructions()

    assert "execute_code" in instructions
    assert "run_command" in instructions
    assert "read_file" in instructions
    assert "Example" in instructions


def test_generate_stubs_has_header():
    """Stubs start with a header comment."""
    stubs = generate_stubs()

    assert stubs.startswith("# External functions available in sandbox")


def test_generate_stubs_uses_ellipsis():
    """Stubs use ... for empty function bodies."""
    stubs = generate_stubs()

    assert "..." in stubs


# ============================================================================
# Command Splitting Tests (for run_command auto-splitting)
# ============================================================================


def test_shlex_split_basic():
    """Verify shlex.split handles basic commands."""
    command = "grep -r pattern ."
    parts = shlex.split(command)
    assert parts == ["grep", "-r", "pattern", "."]


def test_shlex_split_with_quotes():
    """Verify shlex.split handles quoted arguments."""
    command = 'grep -r "class.*Protocol" . --include "*.py"'
    parts = shlex.split(command)
    assert parts == ["grep", "-r", "class.*Protocol", ".", "--include", "*.py"]


def test_shlex_split_preserves_quotes_content():
    """Verify quoted content is preserved without quotes."""
    command = "echo 'hello world'"
    parts = shlex.split(command)
    assert parts == ["echo", "hello world"]


def test_command_split_logic():
    """Test the logic that will be used in run_command."""
    command = 'grep -r "class.*Protocol" . --include "*.py"'
    args = None

    # This is the logic from run_command
    if args is None and ' ' in command:
        try:
            parts = shlex.split(command)
            if len(parts) > 1:
                command = parts[0]
                args = parts[1:]
        except ValueError:
            pass

    assert command == "grep"
    assert args == ["-r", "class.*Protocol", ".", "--include", "*.py"]


def test_command_split_with_existing_args():
    """Verify existing args are preserved when provided."""
    command = "grep"
    args = ["-r", "pattern"]

    # Logic should NOT split when args already provided
    if args is None and ' ' in command:
        parts = shlex.split(command)
        if len(parts) > 1:
            command = parts[0]
            args = parts[1:]

    assert command == "grep"
    assert args == ["-r", "pattern"]  # Original args preserved


def test_command_split_no_spaces():
    """Verify single command without spaces is unchanged."""
    command = "ls"
    args = None

    if args is None and ' ' in command:
        parts = shlex.split(command)
        if len(parts) > 1:
            command = parts[0]
            args = parts[1:]

    assert command == "ls"
    assert args is None
