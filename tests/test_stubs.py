"""Tests for function stub generation from toolset."""

from punie.agent.stubs import generate_stubs, get_stub_instructions


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

    assert "<tool_call>" in instructions
    assert "execute_code" in instructions
    assert "run_command" in instructions
    assert "read_file" in instructions


def test_generate_stubs_has_header():
    """Stubs start with a header comment."""
    stubs = generate_stubs()

    assert stubs.startswith("# External functions available in sandbox")


def test_generate_stubs_uses_ellipsis():
    """Stubs use ... for empty function bodies."""
    stubs = generate_stubs()

    assert "..." in stubs
