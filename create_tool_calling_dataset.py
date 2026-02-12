"""Create synthetic tool-calling training dataset.

Generates 200+ examples demonstrating proper tool usage for Punie's tools:
- read_file
- write_file
- run_command

Run: uv run python create_tool_calling_dataset.py
"""

import json
from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_io import write_dataset


def create_read_file_examples() -> list[TrainingExample]:
    """Create examples for read_file tool."""
    scenarios = [
        ("Read the main.py file", "src/main.py"),
        ("Show me the contents of config.json", "config.json"),
        ("What's in the README file?", "README.md"),
        ("Read the test file", "tests/test_main.py"),
        ("Check the setup.py file", "setup.py"),
        ("Look at the requirements.txt", "requirements.txt"),
        ("Read the LICENSE file", "LICENSE"),
        ("Show the .gitignore file", ".gitignore"),
        ("What's in the package.json?", "package.json"),
        ("Read the Dockerfile", "Dockerfile"),
    ]

    examples = []
    for i, (user_request, file_path) in enumerate(scenarios):
        # Vary the requests
        variations = [
            user_request,
            f"Can you {user_request.lower()}?",
            f"I need to see {file_path}",
            f"Please read {file_path}",
        ]

        for var_idx, variation in enumerate(variations):
            example_num = i * len(variations) + var_idx + 1

            # Tool call message
            tool_call = {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": file_path})
                }
            }

            messages = (
                ChatMessage(role="system", content="You are a helpful coding assistant."),
                ChatMessage(role="user", content=f"{variation} (request {example_num})"),
                ChatMessage(
                    role="assistant",
                    content=f"I'll read the file for you.\n\nTool call: {json.dumps(tool_call)}"
                ),
            )
            examples.append(TrainingExample(messages=messages))

    return examples


def create_write_file_examples() -> list[TrainingExample]:
    """Create examples for write_file tool."""
    scenarios = [
        ("Create a hello.py file with a print statement", "hello.py", "print('Hello, World!')"),
        ("Write a simple test file", "test.py", "def test_example():\n    assert True"),
        ("Make a README file", "README.md", "# My Project\n\nDescription here"),
        ("Create a .gitignore", ".gitignore", "*.pyc\n__pycache__/\n.env"),
        ("Write a requirements file", "requirements.txt", "pytest>=7.0\nrequests>=2.28"),
        ("Create a simple HTML file", "index.html", "<!DOCTYPE html>\n<html>\n<body>Hello</body>\n</html>"),
        ("Make a Dockerfile", "Dockerfile", "FROM python:3.11\nWORKDIR /app"),
        ("Create a config file", "config.json", '{"debug": true}'),
    ]

    examples = []
    for i, (user_request, file_path, content) in enumerate(scenarios):
        variations = [
            user_request,
            f"Please {user_request.lower()}",
            f"I need a {file_path} file",
        ]

        for var_idx, variation in enumerate(variations):
            example_num = i * len(variations) + var_idx + 1

            tool_call = {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": json.dumps({"path": file_path, "content": content})
                }
            }

            messages = (
                ChatMessage(role="system", content="You are a helpful coding assistant."),
                ChatMessage(role="user", content=f"{variation} (request {example_num})"),
                ChatMessage(
                    role="assistant",
                    content=f"I'll create that file for you.\n\nTool call: {json.dumps(tool_call)}"
                ),
            )
            examples.append(TrainingExample(messages=messages))

    return examples


def create_run_command_examples() -> list[TrainingExample]:
    """Create examples for run_command tool."""
    scenarios = [
        ("Run the tests", "pytest"),
        ("Install dependencies", "pip install -r requirements.txt"),
        ("Check git status", "git status"),
        ("List files in current directory", "ls -la"),
        ("Run the linter", "ruff check ."),
        ("Format the code", "ruff format ."),
        ("Start the server", "python manage.py runserver"),
        ("Build the project", "npm run build"),
        ("Run type checker", "mypy ."),
        ("Execute main.py", "python main.py"),
    ]

    examples = []
    for i, (user_request, command) in enumerate(scenarios):
        variations = [
            user_request,
            f"Can you {user_request.lower()}?",
            f"Please run: {command}",
            f"Execute {command}",
        ]

        for var_idx, variation in enumerate(variations):
            example_num = i * len(variations) + var_idx + 1

            tool_call = {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "arguments": json.dumps({"command": command})
                }
            }

            messages = (
                ChatMessage(role="system", content="You are a helpful coding assistant."),
                ChatMessage(role="user", content=f"{variation} (request {example_num})"),
                ChatMessage(
                    role="assistant",
                    content=f"I'll run that command for you.\n\nTool call: {json.dumps(tool_call)}"
                ),
            )
            examples.append(TrainingExample(messages=messages))

    return examples


def create_multi_step_examples() -> list[TrainingExample]:
    """Create examples combining multiple tools."""
    scenarios = [
        ("Read main.py and then run it", [
            ("read_file", {"path": "main.py"}),
            ("run_command", {"command": "python main.py"}),
        ]),
        ("Check the test file and run tests", [
            ("read_file", {"path": "tests/test_main.py"}),
            ("run_command", {"command": "pytest"}),
        ]),
        ("Create a hello.py file and execute it", [
            ("write_file", {"path": "hello.py", "content": "print('Hello')"}),
            ("run_command", {"command": "python hello.py"}),
        ]),
    ]

    examples = []
    for i, (user_request, steps) in enumerate(scenarios):
        example_num = i + 1

        # Create response showing first step
        first_tool, first_args = steps[0]
        tool_call = {
            "type": "function",
            "function": {
                "name": first_tool,
                "arguments": json.dumps(first_args)
            }
        }

        messages = (
            ChatMessage(role="system", content="You are a helpful coding assistant."),
            ChatMessage(role="user", content=f"{user_request} (request {example_num})"),
            ChatMessage(
                role="assistant",
                content=f"I'll help you with that. First, let me {first_tool.replace('_', ' ')}.\n\nTool call: {json.dumps(tool_call)}"
            ),
        )
        examples.append(TrainingExample(messages=messages))

    return examples


def main():
    """Generate tool-calling training dataset."""
    print("=" * 70)
    print("🔧 Creating Tool-Calling Training Dataset")
    print("=" * 70)

    print("\nGenerating examples for Punie's tools...")
    read_examples = create_read_file_examples()  # 40 examples (10 scenarios * 4 variations)
    write_examples = create_write_file_examples()  # 24 examples (8 scenarios * 3 variations)
    command_examples = create_run_command_examples()  # 40 examples (10 scenarios * 4 variations)
    multi_examples = create_multi_step_examples()  # 3 examples

    all_examples = read_examples + write_examples + command_examples + multi_examples

    print(f"✅ Generated {len(all_examples)} examples")
    print(f"   read_file: {len(read_examples)}")
    print(f"   write_file: {len(write_examples)}")
    print(f"   run_command: {len(command_examples)}")
    print(f"   multi-step: {len(multi_examples)}")

    # Split 80/10/10
    total = len(all_examples)
    train_end = int(total * 0.8)
    valid_end = int(total * 0.9)

    dataset = TrainingDataset(
        name="tool-calling-synthetic",
        version="1.0",
        train=tuple(all_examples[:train_end]),
        valid=tuple(all_examples[train_end:valid_end]),
        test=tuple(all_examples[valid_end:]),
    )

    output_dir = Path("data/synthetic/tool-calling")
    write_dataset(dataset, output_dir)

    print(f"\n📊 Dataset Split:")
    print(f"   Train: {len(dataset.train)} examples")
    print(f"   Valid: {len(dataset.valid)} examples")
    print(f"   Test: {len(dataset.test)} examples")

    print(f"\n✅ Saved to: {output_dir}/")

    print("\n💡 This dataset demonstrates:")
    print("   - Proper tool call format")
    print("   - Punie's actual tools (read_file, write_file, run_command)")
    print("   - Realistic scenarios")
    print("   - Multi-step workflows")

    print("\n" + "=" * 70)
    print("Dataset ready for tool-calling training!")
    print("=" * 70)


if __name__ == "__main__":
    main()
