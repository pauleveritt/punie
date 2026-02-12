"""Tests for tool calling templates."""

from punie.training.tool_calling_templates import (
    ToolCallExample,
    create_read_file_example,
    create_write_file_example,
    create_run_command_example,
    create_multi_tool_example,
)


def test_tool_call_example_frozen():
    """ToolCallExample is immutable."""
    example = ToolCallExample(
        system_message="system",
        user_request="request",
        tool_name="read_file",
        tool_arguments='{"path": "test.py"}',
        tool_result="content",
        assistant_response="response",
    )

    try:
        example.tool_name = "write_file"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_tool_call_example_to_training_example():
    """ToolCallExample converts to correct message sequence."""
    example = ToolCallExample(
        system_message="You are a helpful assistant.",
        user_request="Read the file test.py",
        tool_name="read_file",
        tool_arguments='{"path": "test.py"}',
        tool_result="print('hello')",
        assistant_response="The file contains a simple print statement.",
    )

    training_example = example.to_training_example()

    # Should have 5 messages: system, user, assistant (tool call), user (result), assistant (final)
    assert len(training_example.messages) == 5

    assert training_example.messages[0].role == "system"
    assert training_example.messages[0].content == "You are a helpful assistant."

    assert training_example.messages[1].role == "user"
    assert training_example.messages[1].content == "Read the file test.py"

    assert training_example.messages[2].role == "assistant"
    assert "<tool_call>" in training_example.messages[2].content
    assert '"name": "read_file"' in training_example.messages[2].content
    assert '"path": "test.py"' in training_example.messages[2].content

    assert training_example.messages[3].role == "user"
    assert "Tool result:" in training_example.messages[3].content
    assert "print('hello')" in training_example.messages[3].content

    assert training_example.messages[4].role == "assistant"
    assert training_example.messages[4].content == "The file contains a simple print statement."


def test_create_read_file_example():
    """create_read_file_example produces valid training example."""
    example = create_read_file_example(
        file_path="src/main.py",
        file_content="def main():\n    pass",
        user_question="What does main.py do?",
        assistant_answer="The file defines an empty main function.",
    )

    assert len(example.messages) == 5
    assert example.messages[1].content == "What does main.py do?"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "read_file"' in example.messages[2].content
    assert "src/main.py" in example.messages[2].content
    assert "def main()" in example.messages[3].content
    assert "empty main function" in example.messages[4].content


def test_create_write_file_example():
    """create_write_file_example produces valid training example."""
    example = create_write_file_example(
        file_path="test.txt",
        new_content="Hello, World!",
        user_request="Create a test file with hello world",
        confirmation_message="I've created test.txt with the message.",
    )

    assert len(example.messages) == 5
    assert example.messages[1].content == "Create a test file with hello world"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "write_file"' in example.messages[2].content
    assert "test.txt" in example.messages[2].content
    assert "File written successfully" in example.messages[3].content
    assert "created test.txt" in example.messages[4].content


def test_create_run_command_example():
    """create_run_command_example produces valid training example."""
    example = create_run_command_example(
        command="pytest tests/",
        output="5 passed in 0.1s",
        user_request="Run the tests",
        assistant_interpretation="All 5 tests passed successfully!",
    )

    assert len(example.messages) == 5
    assert example.messages[1].content == "Run the tests"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "run_command"' in example.messages[2].content
    assert "pytest tests/" in example.messages[2].content
    assert "5 passed" in example.messages[3].content
    assert "All 5 tests passed" in example.messages[4].content


def test_create_multi_tool_example():
    """create_multi_tool_example handles multiple tool calls."""
    example = create_multi_tool_example(
        system_message="You are Punie.",
        user_request="Read main.py and run the tests",
        tool_sequence=[
            ("read_file", '{"path": "main.py"}', "def main(): pass"),
            ("run_command", '{"command": "pytest"}', "3 passed"),
        ],
        final_response="I read main.py and ran the tests. All 3 tests passed.",
    )

    # System + user + (assistant + user) * 2 tools + final assistant = 7 messages
    assert len(example.messages) == 7

    assert example.messages[0].role == "system"
    assert example.messages[1].role == "user"

    # First tool call
    assert example.messages[2].role == "assistant"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "read_file"' in example.messages[2].content
    assert example.messages[3].role == "user"
    assert "def main()" in example.messages[3].content

    # Second tool call
    assert example.messages[4].role == "assistant"
    assert "<tool_call>" in example.messages[4].content
    assert '"name": "run_command"' in example.messages[4].content
    assert example.messages[5].role == "user"
    assert "3 passed" in example.messages[5].content

    # Final response
    assert example.messages[6].role == "assistant"
    assert "All 3 tests passed" in example.messages[6].content


def test_create_multi_tool_example_single_tool():
    """create_multi_tool_example works with single tool."""
    example = create_multi_tool_example(
        system_message="System",
        user_request="Read file",
        tool_sequence=[
            ("read_file", '{"path": "test.py"}', "content"),
        ],
        final_response="Done",
    )

    # System + user + assistant + user + assistant = 5 messages
    assert len(example.messages) == 5
