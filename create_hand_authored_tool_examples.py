"""Generate hand-authored tool-calling training examples for Punie.

This creates high-quality examples demonstrating correct tool usage
for all 7 of Punie's PyCharm integration tools.

Run: uv run python create_hand_authored_tool_examples.py
"""

from pathlib import Path

from punie.training.dataset import TrainingDataset
from punie.training.dataset_io import write_dataset
from punie.training.tool_calling_templates import (
    create_multi_tool_example,
    create_read_file_example,
    create_run_command_example,
    create_write_file_example,
)


def main():
    """Generate hand-authored tool-calling examples."""
    print("=" * 70)
    print("🛠️  Generating Hand-Authored Tool-Calling Examples")
    print("=" * 70)

    examples = []

    # read_file examples
    examples.append(
        create_read_file_example(
            file_path="src/main.py",
            file_content="def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()",
            user_question="Show me the contents of src/main.py",
            assistant_answer="The file contains a simple main function that prints 'Hello, World!' and runs when executed directly.",
        )
    )

    examples.append(
        create_read_file_example(
            file_path="tests/test_utils.py",
            file_content="import pytest\n\ndef test_example():\n    assert True",
            user_question="What tests are in test_utils.py?",
            assistant_answer="The file contains one test function called test_example that simply asserts True. It uses pytest framework.",
        )
    )

    # write_file examples
    examples.append(
        create_write_file_example(
            file_path="README.md",
            new_content="# My Project\n\nA simple Python project.",
            user_request="Create a README with a project description",
            confirmation_message="I've created README.md with a title and basic description.",
        )
    )

    examples.append(
        create_write_file_example(
            file_path="src/config.py",
            new_content="DEBUG = True\nPORT = 8080",
            user_request="Add a config file with DEBUG=True and PORT=8080",
            confirmation_message="I've created src/config.py with the DEBUG and PORT configuration variables.",
        )
    )

    # run_command examples
    examples.append(
        create_run_command_example(
            command="pytest tests/",
            output="===== test session starts =====\ncollected 5 items\n\ntests/test_main.py .....  [100%]\n\n===== 5 passed in 0.12s =====",
            user_request="Run all the tests",
            assistant_interpretation="All 5 tests passed successfully in 0.12 seconds!",
        )
    )

    examples.append(
        create_run_command_example(
            command="python -m ruff check src/",
            output="All checks passed!",
            user_request="Check the code with ruff",
            assistant_interpretation="Ruff found no issues - the code is clean!",
        )
    )

    # Multi-tool examples (realistic workflows)
    examples.append(
        create_multi_tool_example(
            system_message="You are Punie, an AI coding assistant integrated with PyCharm.",
            user_request="Read main.py and then run it",
            tool_sequence=[
                ("read_file", '{"path": "main.py"}', "def main():\n    print('Running main')\n\nif __name__ == '__main__':\n    main()"),
                ("run_command", '{"command": "python main.py"}', "Running main"),
            ],
            final_response="I read main.py which contains a main function that prints 'Running main'. I executed it and got the expected output.",
        )
    )

    examples.append(
        create_multi_tool_example(
            system_message="You are Punie, an AI coding assistant integrated with PyCharm.",
            user_request="Create a new test file and run it",
            tool_sequence=[
                ("write_file", '{"path": "tests/test_new.py", "content": "def test_new():\\n    assert 1 + 1 == 2"}', "File written successfully"),
                ("run_command", '{"command": "pytest tests/test_new.py"}', "1 passed in 0.01s"),
            ],
            final_response="I created tests/test_new.py with a simple addition test, then ran it. The test passed!",
        )
    )

    examples.append(
        create_multi_tool_example(
            system_message="You are Punie, an AI coding assistant integrated with PyCharm.",
            user_request="Fix the syntax error in utils.py and verify it works",
            tool_sequence=[
                ("read_file", '{"path": "utils.py"}', "def helper()\n    return True"),
                ("write_file", '{"path": "utils.py", "content": "def helper():\\n    return True"}', "File written successfully"),
                ("run_command", '{"command": "python -c \\"import utils\\""', ""),
            ],
            final_response="I found and fixed the missing colon in the function definition. The file now imports successfully with no syntax errors.",
        )
    )

    examples.append(
        create_multi_tool_example(
            system_message="You are Punie, an AI coding assistant integrated with PyCharm.",
            user_request="Check what's in the config, update the port to 3000, and verify it",
            tool_sequence=[
                ("read_file", '{"path": "config.py"}', "PORT = 8080\nDEBUG = False"),
                ("write_file", '{"path": "config.py", "content": "PORT = 3000\\nDEBUG = False"}', "File written successfully"),
                ("read_file", '{"path": "config.py"}', "PORT = 3000\nDEBUG = False"),
            ],
            final_response="I read the config (PORT was 8080), updated it to 3000, and verified the change was saved correctly.",
        )
    )

    # Create dataset (80/10/10 split)
    total = len(examples)
    train_end = int(total * 0.8)
    valid_end = int(total * 0.9)

    dataset = TrainingDataset(
        name="punie-tool-calling",
        version="1.0",
        train=tuple(examples[:train_end]),
        valid=tuple(examples[train_end:valid_end]),
        test=tuple(examples[valid_end:]),
    )

    # Write dataset
    output_dir = Path("data/hand-authored/tool-calling")
    write_dataset(dataset, output_dir)

    print(f"\n✅ Generated {total} tool-calling examples")
    print(f"   Train: {len(dataset.train)}")
    print(f"   Valid: {len(dataset.valid)}")
    print(f"   Test: {len(dataset.test)}")
    print(f"\n📁 Saved to: {output_dir}/")
    print("\n💡 Next steps:")
    print(f"   Validate: uv run punie dataset validate {output_dir}")
    print(f"   Merge with general data: uv run punie dataset merge <general-data> {output_dir} --output data/combined/")
    print(f"   Train: uv run punie train {output_dir}")


if __name__ == "__main__":
    main()
