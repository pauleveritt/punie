"""Generate domain-specific training examples from t-strings repos.

Reads real example and test files from tdom-svcs, svcs-di, storyville, and aria-testing
to create training data that teaches the model actual Python/DI/tdom patterns.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Base directory for t-strings repos
T_STRINGS_BASE = Path("/Users/pauleveritt/projects/t-strings")

# System message for all examples
SYSTEM_MSG = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."


@dataclass
class Example:
    """A single training example."""

    user_query: str
    tool_name: str | None  # None for direct answers
    tool_args: dict[str, Any] | None
    tool_result: str | None
    final_response: str


def create_messages(example: Example) -> dict[str, list[dict[str, str]]]:
    """Convert an Example to the messages format."""
    messages = [
        {"role": "system", "content": SYSTEM_MSG},
        {"role": "user", "content": example.user_query},
    ]

    if example.tool_name:
        # Assistant calls tool
        tool_call = {
            "role": "assistant",
            "content": f"I'll use the {example.tool_name} tool.\n\n```json\n{json.dumps({'name': example.tool_name, 'arguments': example.tool_args}, indent=2)}\n```",
        }
        messages.append(tool_call)

        # Tool result
        messages.append({"role": "user", "content": f"Tool result: {example.tool_result}"})

    # Final response
    messages.append({"role": "assistant", "content": example.final_response})

    return {"messages": messages}


def read_file_safe(path: Path) -> str | None:
    """Read file, return None if it doesn't exist or is too large."""
    try:
        if not path.exists() or path.stat().st_size > 50_000:
            return None
        return path.read_text()
    except Exception:
        return None


def generate_read_file_examples() -> list[Example]:
    """Generate read_file examples from real source files."""
    examples = []

    # svcs-di examples
    files_to_read = [
        ("svcs-di/examples/basic_injection.py", "Show me the basic injection example", "basic injection pattern"),
        ("svcs-di/examples/basic_function.py", "What's in the basic function example?", "function-based DI example"),
        ("svcs-di/examples/modern_dataclass.py", "Show me the modern dataclass example", "advanced dataclass features"),
        ("svcs-di/examples/protocol_injection.py", "Show me protocol injection", "protocol-based DI"),
    ]

    # tdom-svcs examples
    files_to_read.extend(
        [
            ("tdom-svcs/examples/basic/pure_tdom.py", "Show me pure tdom example", "basic tdom component"),
            ("tdom-svcs/examples/basic/inject_service.py", "Show me service injection in tdom", "tdom with DI"),
            (
                "tdom-svcs/examples/hopscotch/simple_inject.py",
                "Show me Hopscotch injection",
                "Hopscotch DI pattern",
            ),
        ]
    )

    for file_path, query, description in files_to_read:
        full_path = T_STRINGS_BASE / file_path
        content = read_file_safe(full_path)
        if content:
            examples.append(
                Example(
                    user_query=query,
                    tool_name="read_file",
                    tool_args={"path": file_path},
                    tool_result=content,
                    final_response=f"This file shows {description}. It demonstrates the key patterns for this approach.",
                )
            )

    return examples


def generate_test_file_examples() -> list[Example]:
    """Generate examples from test files."""
    examples = []

    test_files = [
        (
            "svcs-di/tests/test_injectable.py",
            "Show me the injectable tests",
            "type introspection and Inject marker testing",
        ),
        ("svcs-di/tests/test_auto.py", "What tests cover the auto() function?", "auto() factory testing"),
        (
            "tdom-svcs/tests/test_di_injection.py",
            "Show me DI injection tests",
            "dependency injection with tdom components",
        ),
        (
            "aria-testing/tests/test_queries.py",
            "Show me ARIA query tests",
            "comprehensive accessibility query testing",
        ),
    ]

    for file_path, query, description in test_files:
        full_path = T_STRINGS_BASE / file_path
        content = read_file_safe(full_path)
        if content:
            # Truncate long test files
            if len(content) > 3000:
                lines = content.split("\n")
                content = "\n".join(lines[:80]) + "\n... (truncated)"

            examples.append(
                Example(
                    user_query=query,
                    tool_name="read_file",
                    tool_args={"path": file_path},
                    tool_result=content,
                    final_response=f"This test file covers {description}. The tests use pytest with fixtures and parametrize.",
                )
            )

    return examples


def generate_run_command_examples() -> list[Example]:
    """Generate run_command examples (search, test execution, etc.)."""
    examples = [
        Example(
            user_query="Find all files using Inject in svcs-di",
            tool_name="run_command",
            tool_args={"command": "grep -r 'Inject\\[' svcs-di/"},
            tool_result="svcs-di/examples/basic_injection.py:    db: Inject[Database]\nsvcs-di/src/svcs_di/auto.py:Inject: TypeAlias = Annotated[T, InjectionMarker()]\nsvcs-di/tests/test_injectable.py:    assert extract_inner_type(Inject[Database]) is Database",
            final_response="Found 3 files using Inject: the basic injection example, the auto module where it's defined, and the tests.",
        ),
        Example(
            user_query="Run the svcs-di tests",
            tool_name="run_command",
            tool_args={"command": "cd svcs-di && pytest tests/ -v"},
            tool_result="===== test session starts =====\nplatform darwin -- Python 3.14.2, pytest-9.0.2\ncollected 47 items\n\ntests/test_auto.py::test_auto_creates_factory PASSED\ntests/test_injectable.py::test_injectable_wraps_type PASSED\n... (45 more tests)\n\n===== 47 passed in 1.23s =====",
            final_response="All 47 tests passed successfully in 1.23 seconds!",
        ),
        Example(
            user_query="Find tdom component definitions",
            tool_name="run_command",
            tool_args={"command": "grep -r '@component' tdom-svcs/examples/"},
            tool_result="tdom-svcs/examples/basic/pure_tdom.py:@component\ntdom-svcs/examples/middleware/request_context.py:@component\ntdom-svcs/examples/hopscotch/category_components.py:@component",
            final_response="Found component decorators in 3 files: pure_tdom.py, request_context.py, and category_components.py.",
        ),
    ]

    return examples


def generate_multi_file_examples() -> list[Example]:
    """Generate examples that explore multiple files."""
    # These are simulated multi-turn conversations, but we'll create single-tool versions
    examples = [
        Example(
            user_query="Show me conftest.py in svcs-di",
            tool_name="read_file",
            tool_args={"path": "svcs-di/tests/conftest.py"},
            tool_result='"""Pytest configuration and shared fixtures."""\nimport pytest\nfrom svcs import Container, Registry\n\n\n@pytest.fixture\ndef registry():\n    """Shared registry fixture."""\n    return Registry()\n\n\n@pytest.fixture\ndef container(registry):\n    """Container with fresh registry."""\n    return Container(registry)',
            final_response="The conftest defines shared pytest fixtures: a registry fixture and a container fixture that uses it. These are used across all tests.",
        ),
        Example(
            user_query="Show me test_examples.py in tdom-svcs",
            tool_name="read_file",
            tool_args={"path": "tdom-svcs/tests/test_examples.py"},
            tool_result='"""Run all examples as tests using dynamic parametrization."""\nimport pytest\nfrom pathlib import Path\n\n# Discover all example files\nEXAMPLES_DIR = Path(__file__).parent.parent / "examples"\nexample_files = list(EXAMPLES_DIR.rglob("*.py"))\n\n\n@pytest.mark.parametrize("example_file", example_files)\ndef test_example_runs(example_file):\n    """Each example should run without errors."""\n    exec(example_file.read_text())',
            final_response="This test discovers all example files dynamically and runs each one as a separate test using pytest.mark.parametrize. Smart pattern for validating examples!",
        ),
    ]

    return examples


def generate_direct_answer_examples() -> list[Example]:
    """Generate examples where no tool is needed."""
    examples = [
        Example(
            user_query="What is Inject in svcs-di?",
            tool_name=None,
            tool_args=None,
            tool_result=None,
            final_response="Inject[T] is a type alias in svcs-di that marks a dataclass field for automatic dependency injection. When you use Inject[Database], svcs-di will automatically resolve and inject the Database service from the container.",
        ),
        Example(
            user_query="Explain the difference between svcs and svcs-di",
            tool_name=None,
            tool_args=None,
            tool_result=None,
            final_response="svcs is the core service locator library that provides Registry and Container for manual service registration and retrieval. svcs-di builds on top of svcs to add automatic dependency injection via the Inject marker and auto() factory, eliminating boilerplate.",
        ),
        Example(
            user_query="What is tdom?",
            tool_name=None,
            tool_args=None,
            tool_result=None,
            final_response="tdom is a Python library for building HTML components using PEP 750 t-strings (template strings). It provides a type-safe, composable way to create HTML without templates, leveraging Python's new interpolation syntax.",
        ),
        Example(
            user_query="What does the @component decorator do?",
            tool_name=None,
            tool_args=None,
            tool_result=None,
            final_response="The @component decorator in tdom marks a function as a reusable UI component. It enables the function to return HTML via t-strings and makes it compatible with tdom's rendering pipeline.",
        ),
        Example(
            user_query="What is Hopscotch?",
            tool_name=None,
            tool_args=None,
            tool_result=None,
            final_response="Hopscotch is an advanced dependency injection framework built on svcs-di. It adds features like category-based service resolution, package scanning for auto-discovery, and location-aware routing.",
        ),
    ]

    return examples


def generate_write_file_examples() -> list[Example]:
    """Generate write_file examples."""
    examples = [
        Example(
            user_query="Create a new service class",
            tool_name="write_file",
            tool_args={
                "path": "src/services/user_service.py",
                "content": '"""User service."""\nfrom dataclasses import dataclass\n\n\n@dataclass\nclass UserService:\n    """Service for user operations."""\n\n    db: Database\n\n    def get_user(self, user_id: int) -> User:\n        """Fetch user by ID."""\n        return self.db.query(User, user_id)',
            },
            tool_result="File written successfully",
            final_response="Created UserService with a database dependency and get_user method.",
        ),
        Example(
            user_query="Create a tdom component",
            tool_name="write_file",
            tool_args={
                "path": "src/components/greeting.py",
                "content": '"""Greeting component."""\nfrom tdom import component\n\n\n@component\ndef greeting(name: str) -> str:\n    """Render a greeting."""\n    return t"<div>Hello, {name}!</div>"',
            },
            tool_result="File written successfully",
            final_response="Created a greeting component that takes a name and renders it in a div.",
        ),
    ]

    return examples


def main():
    """Generate all domain examples and write to output file."""
    all_examples = []

    print("Generating read_file examples...")
    all_examples.extend(generate_read_file_examples())

    print("Generating test file examples...")
    all_examples.extend(generate_test_file_examples())

    print("Generating run_command examples...")
    all_examples.extend(generate_run_command_examples())

    print("Generating multi-file examples...")
    all_examples.extend(generate_multi_file_examples())

    print("Generating direct answer examples...")
    all_examples.extend(generate_direct_answer_examples())

    print("Generating write_file examples...")
    all_examples.extend(generate_write_file_examples())

    # Convert to messages format
    messages = [create_messages(ex) for ex in all_examples]

    # Write to output file
    output_path = Path(__file__).parent.parent / "data" / "domain_examples.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    print(f"\nGenerated {len(messages)} domain examples -> {output_path}")
    print(f"  - {len(generate_read_file_examples())} read_file examples")
    print(f"  - {len(generate_test_file_examples())} test file examples")
    print(f"  - {len(generate_run_command_examples())} run_command examples")
    print(f"  - {len(generate_multi_file_examples())} multi-file examples")
    print(f"  - {len(generate_direct_answer_examples())} direct answer examples")
    print(f"  - {len(generate_write_file_examples())} write_file examples")


if __name__ == "__main__":
    main()
