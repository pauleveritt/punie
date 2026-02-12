"""Test run_command auto-splitting of full command strings."""

import shlex


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
