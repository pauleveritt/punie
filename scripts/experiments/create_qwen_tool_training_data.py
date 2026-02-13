"""Create training data for Qwen function calling format.

Based on Qwen's documentation, the model expects function definitions in the
system message and generates function calls in a specific format.
"""

from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingExample
from punie.training.dataset_io import write_jsonl


def create_qwen_tool_training_examples() -> tuple[TrainingExample, ...]:
    """Create training examples for Qwen function calling.

    Qwen models expect:
    1. Function definitions in system message (JSON schema format)
    2. Function calls in response with specific format

    Returns:
        Tuple of TrainingExample instances
    """
    # Tool definitions in Qwen format
    tools_definition = """You are a helpful coding assistant with access to these functions:

[
  {
    "name": "read_file",
    "description": "Read the contents of a file",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "The file path to read"}
      },
      "required": ["path"]
    }
  },
  {
    "name": "write_file",
    "description": "Write content to a file",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "The file path to write"},
        "content": {"type": "string", "description": "The content to write"}
      },
      "required": ["path", "content"]
    }
  },
  {
    "name": "run_command",
    "description": "Execute a shell command",
    "parameters": {
      "type": "object",
      "properties": {
        "command": {"type": "string", "description": "The command to execute"}
      },
      "required": ["command"]
    }
  },
  {
    "name": "list_dir",
    "description": "List files in a directory",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Directory path (default: current)"}
      }
    }
  }
]

When you need to call a function, respond with:
<tool_call>
{"name": "function_name", "arguments": {...}}
</tool_call>"""

    examples = []

    # Example 1: read_file
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="Read the file at /etc/hosts and tell me what's in it."),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "read_file", "arguments": {"path": "/etc/hosts"}}\n</tool_call>'),
        )
    ))

    # Example 2: write_file
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="Create a file called test.txt with the content 'Hello World'."),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "write_file", "arguments": {"path": "test.txt", "content": "Hello World"}}\n</tool_call>'),
        )
    ))

    # Example 3: run_command
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="Run the command 'echo hello' and show me the output."),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "run_command", "arguments": {"command": "echo hello"}}\n</tool_call>'),
        )
    ))

    # Example 4: list_dir
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="List all files in the current directory."),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "list_dir", "arguments": {"path": "."}}\n</tool_call>'),
        )
    ))

    # Example 5: read_file with common path
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="Show me the contents of README.md"),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "read_file", "arguments": {"path": "README.md"}}\n</tool_call>'),
        )
    ))

    # Example 6: write_file with Python code
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="Create a file main.py with a simple hello world function."),
            ChatMessage(role="assistant", content=r'<tool_call>\n{"name": "write_file", "arguments": {"path": "main.py", "content": "def hello():\n    print(\'Hello, World!\')\n\nif __name__ == \'__main__\':\n    hello()"}}\n</tool_call>'),
        )
    ))

    # Example 7: list_dir for source files
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="List all Python files in the src directory."),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "list_dir", "arguments": {"path": "src"}}\n</tool_call>'),
        )
    ))

    # Example 8: run_command for git
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="Show me the git status."),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "run_command", "arguments": {"command": "git status"}}\n</tool_call>'),
        )
    ))

    # Example 9: Multiple variations for read_file
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="What's in the config.json file?"),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "read_file", "arguments": {"path": "config.json"}}\n</tool_call>'),
        )
    ))

    # Example 10: run_command for testing
    examples.append(TrainingExample(
        messages=(
            ChatMessage(role="system", content=tools_definition),
            ChatMessage(role="user", content="Run the tests."),
            ChatMessage(role="assistant", content='<tool_call>\n{"name": "run_command", "arguments": {"command": "pytest"}}\n</tool_call>'),
        )
    ))

    return tuple(examples)


def main():
    """Create and save Qwen tool-calling training dataset."""
    print("Creating Qwen tool-calling training dataset...")

    examples = create_qwen_tool_training_examples()

    # Split: 8 train, 1 valid, 1 test
    train_examples = examples[:8]
    valid_examples = examples[8:9]
    test_examples = examples[9:10]

    # Create output directory
    output_dir = Path("data/qwen-tool-calling")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write splits
    write_jsonl(train_examples, output_dir / "train.jsonl")
    write_jsonl(valid_examples, output_dir / "valid.jsonl")
    write_jsonl(test_examples, output_dir / "test.jsonl")

    print(f"✅ Created dataset in {output_dir}/")
    print(f"   Train: {len(train_examples)} examples")
    print(f"   Valid: {len(valid_examples)} examples")
    print(f"   Test: {len(test_examples)} examples")
    print(f"\nNext steps:")
    print(f"1. Train: uv run punie train {output_dir}/ --output adapters/qwen-tool-calling/ --iters 50")
    print(f"2. Eval:  uv run punie eval --adapter adapters/qwen-tool-calling/ --output eval_qwen_tools.html")


if __name__ == "__main__":
    main()
