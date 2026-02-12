"""Templates for creating tool-calling training examples.

Punie has 7 tools for interacting with PyCharm:
1. read_file - Read file contents
2. write_file - Write file contents
3. run_command - Execute shell command
4. get_terminal_output - Get output from running terminal
5. release_terminal - Release terminal control
6. wait_for_terminal_exit - Wait for terminal to finish
7. kill_terminal - Terminate a running terminal
"""

from dataclasses import dataclass

from punie.training.dataset import ChatMessage, TrainingExample


@dataclass(frozen=True)
class ToolCallExample:
    """Helper for creating multi-turn tool-call training examples.

    Represents: user request → assistant tool call → tool result → assistant response
    """

    system_message: str
    user_request: str
    tool_name: str
    tool_arguments: str  # JSON string
    tool_result: str
    assistant_response: str

    def to_training_example(self) -> TrainingExample:
        """Convert to TrainingExample format.

        Creates a multi-turn conversation:
        1. System message
        2. User request
        3. Assistant response with tool call
        4. Tool result (as user message)
        5. Final assistant response
        """
        # Format tool call in the style expected by chat models
        tool_call_response = f"I'll use the {self.tool_name} tool.\n\n```json\n{{\n  \"tool\": \"{self.tool_name}\",\n  \"arguments\": {self.tool_arguments}\n}}\n```"

        messages = (
            ChatMessage(role="system", content=self.system_message),
            ChatMessage(role="user", content=self.user_request),
            ChatMessage(role="assistant", content=tool_call_response),
            ChatMessage(role="user", content=f"Tool result: {self.tool_result}"),
            ChatMessage(role="assistant", content=self.assistant_response),
        )

        return TrainingExample(messages=messages)


def create_read_file_example(
    file_path: str,
    file_content: str,
    user_question: str,
    assistant_answer: str,
) -> TrainingExample:
    """Create training example for read_file tool.

    Args:
        file_path: Path to file being read
        file_content: Content of the file
        user_question: User's question about the file
        assistant_answer: Assistant's answer after reading

    Returns:
        TrainingExample with tool call sequence
    """
    example = ToolCallExample(
        system_message="You are Punie, an AI coding assistant that helps with Python development via PyCharm.",
        user_request=user_question,
        tool_name="read_file",
        tool_arguments=f'{{"path": "{file_path}"}}',
        tool_result=file_content,
        assistant_response=assistant_answer,
    )
    return example.to_training_example()


def create_write_file_example(
    file_path: str,
    new_content: str,
    user_request: str,
    confirmation_message: str,
) -> TrainingExample:
    """Create training example for write_file tool.

    Args:
        file_path: Path to file being written
        new_content: Content to write
        user_request: User's request to write/modify file
        confirmation_message: Assistant's confirmation after writing

    Returns:
        TrainingExample with tool call sequence
    """
    example = ToolCallExample(
        system_message="You are Punie, an AI coding assistant that helps with Python development via PyCharm.",
        user_request=user_request,
        tool_name="write_file",
        tool_arguments=f'{{"path": "{file_path}", "content": {repr(new_content)}}}',
        tool_result="File written successfully",
        assistant_response=confirmation_message,
    )
    return example.to_training_example()


def create_run_command_example(
    command: str,
    output: str,
    user_request: str,
    assistant_interpretation: str,
) -> TrainingExample:
    """Create training example for run_command tool.

    Args:
        command: Shell command to run
        output: Command output
        user_request: User's request to run command
        assistant_interpretation: Assistant's interpretation of results

    Returns:
        TrainingExample with tool call sequence
    """
    example = ToolCallExample(
        system_message="You are Punie, an AI coding assistant that helps with Python development via PyCharm.",
        user_request=user_request,
        tool_name="run_command",
        tool_arguments=f'{{"command": "{command}"}}',
        tool_result=output,
        assistant_response=assistant_interpretation,
    )
    return example.to_training_example()


def create_multi_tool_example(
    system_message: str,
    user_request: str,
    tool_sequence: list[tuple[str, str, str]],  # [(tool_name, arguments, result), ...]
    final_response: str,
) -> TrainingExample:
    """Create training example with multiple tool calls.

    Args:
        system_message: System prompt
        user_request: Initial user request
        tool_sequence: List of (tool_name, arguments_json, result) tuples
        final_response: Final assistant response after all tools

    Returns:
        TrainingExample with multi-tool sequence
    """
    messages = [
        ChatMessage(role="system", content=system_message),
        ChatMessage(role="user", content=user_request),
    ]

    for tool_name, arguments, result in tool_sequence:
        # Assistant makes tool call
        tool_call_response = f"I'll use the {tool_name} tool.\n\n```json\n{{\n  \"tool\": \"{tool_name}\",\n  \"arguments\": {arguments}\n}}\n```"
        messages.append(ChatMessage(role="assistant", content=tool_call_response))

        # Tool result
        messages.append(ChatMessage(role="user", content=f"Tool result: {result}"))

    # Final response
    messages.append(ChatMessage(role="assistant", content=final_response))

    return TrainingExample(messages=tuple(messages))
