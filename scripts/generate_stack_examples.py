#!/usr/bin/env python3
"""Generate tool-calling training examples from Stack v2 Python code.

Takes filtered Python files from Stack v2 and generates:
- grep queries (find classes, functions, patterns)
- read_file queries (show examples, read specific files)
- direct answer queries (concepts, comparisons, best practices)

Output format matches Qwen chat template with tool calls.
"""

import json
import random
import re
from pathlib import Path


def extract_classes(code: str) -> list[str]:
    """Extract class names from Python code."""
    pattern = r"^class\s+(\w+)"
    return re.findall(pattern, code, re.MULTILINE)


def extract_functions(code: str) -> list[str]:
    """Extract function names from Python code."""
    pattern = r"^def\s+(\w+)"
    return re.findall(pattern, code, re.MULTILINE)


def extract_imports(code: str) -> list[str]:
    """Extract import statements."""
    pattern = r"^(?:from\s+(\S+)\s+)?import\s+(.+?)(?:\s+as\s+\S+)?$"
    matches = re.findall(pattern, code, re.MULTILINE)
    imports = []
    for from_module, import_list in matches:
        if from_module:
            imports.append(from_module)
        imports.extend(item.strip() for item in import_list.split(','))
    return imports


def has_decorators(code: str) -> bool:
    """Check if code uses decorators."""
    return bool(re.search(r"^@\w+", code, re.MULTILINE))


def has_async(code: str) -> bool:
    """Check if code uses async/await."""
    return "async " in code or "await " in code


def has_type_hints(code: str) -> bool:
    """Check if code has type hints."""
    return "->" in code or bool(re.search(r":\s*[A-Z]\w+", code))


def generate_grep_example(item: dict) -> dict | None:
    """Generate a grep/search tool-calling example."""
    code = item["content"]
    path = item["path"]

    # Extract features
    classes = extract_classes(code)
    functions = extract_functions(code)

    # Generate query based on what's in the code
    queries = []

    if classes:
        sample_class = random.choice(classes)
        queries.append({
            "query": f"Find all classes that inherit from {sample_class}",
            "tool": "run_command",
            "command": f"grep -r 'class.*{sample_class}' --include='*.py'",
            "result": f"{path}: class {sample_class}(...)",
            "answer": f"Found 1 class that inherits from {sample_class} in {path}.",
        })

    if functions:
        sample_func = random.choice(functions)
        queries.append({
            "query": f"Find all uses of the {sample_func} function",
            "tool": "run_command",
            "command": f"grep -r '{sample_func}(' --include='*.py'",
            "result": f"{path}: {sample_func}(args)",
            "answer": f"Found {sample_func} function defined in {path}.",
        })

    if has_decorators(code):
        queries.append({
            "query": "Find all decorator usage in this codebase",
            "tool": "run_command",
            "command": "grep -r '^@' --include='*.py'",
            "result": f"{path}: @decorator",
            "answer": f"Found decorators in {path}.",
        })

    if not queries:
        return None

    # Pick one query
    selected = random.choice(queries)

    # Format as training example
    return {
        "text": format_chat(
            query=selected["query"],
            tool_name=selected["tool"],
            tool_args={"command": selected["command"]},
            tool_result=selected["result"],
            final_answer=selected["answer"],
        ),
        "source": "stack_grep",
        "category": item.get("category", "other"),
    }


def generate_read_example(item: dict) -> dict | None:
    """Generate a read_file tool-calling example."""
    code = item["content"]
    path = item["path"]

    # Generate query
    queries = []

    if "class " in code:
        queries.append({
            "query": f"Show me the code in {path}",
            "path": path,
            "snippet": code[:200],
        })

    if "def " in code:
        functions = extract_functions(code)
        if functions:
            func = random.choice(functions)
            queries.append({
                "query": f"Show me the implementation of {func}",
                "path": path,
                "snippet": code[:200],
            })

    if not queries:
        return None

    selected = random.choice(queries)

    return {
        "text": format_chat(
            query=selected["query"],
            tool_name="read_file",
            tool_args={"path": selected["path"]},
            tool_result=selected["snippet"] + "\n...",
            final_answer=f"Here's the code from {path}. The file contains {len(code)} characters.",
        ),
        "source": "stack_read",
        "category": item.get("category", "other"),
    }


def generate_direct_example(item: dict) -> dict | None:
    """Generate a direct-answer example (no tools)."""
    code = item["content"]
    category = item.get("category", "other")

    # Generate concept questions based on category and code features
    queries = []

    if category == "async":
        queries.extend([
            {
                "query": "What is async/await in Python?",
                "answer": "Async/await is Python's syntax for asynchronous programming. Functions marked with 'async def' are coroutines that can pause execution with 'await' while waiting for I/O operations, allowing other tasks to run concurrently.",
            },
            {
                "query": "When should I use asyncio?",
                "answer": "Use asyncio when your program does a lot of I/O operations (network requests, file I/O, database queries) where tasks spend time waiting. It's most beneficial for I/O-bound applications like web servers, API clients, or database applications.",
            },
        ])

    if category == "typing" or has_type_hints(code):
        queries.extend([
            {
                "query": "What are type hints in Python?",
                "answer": "Type hints are annotations that specify the expected types of variables, function parameters, and return values. They improve code documentation, enable static type checking with tools like mypy, and help IDEs provide better autocompletion.",
            },
            {
                "query": "What is the difference between Protocol and ABC?",
                "answer": "Protocol enables structural subtyping (duck typing) - any class that implements the required methods automatically satisfies the protocol. ABC (Abstract Base Class) uses nominal subtyping - classes must explicitly inherit from the ABC. Protocol is more flexible and Pythonic.",
            },
        ])

    if category == "testing":
        queries.extend([
            {
                "query": "What is the difference between fixtures and mocks in pytest?",
                "answer": "Fixtures provide reusable test setup/teardown logic and can inject dependencies into tests. Mocks are test doubles that replace real objects to isolate code under test. Fixtures manage test resources, mocks control test behavior and verify interactions.",
            },
            {
                "query": "When should I use parametrize in pytest?",
                "answer": "Use @pytest.mark.parametrize when you want to run the same test with different input values. It's cleaner than writing multiple similar test functions and makes it easy to add more test cases by just adding to the parameter list.",
            },
        ])

    if category == "web":
        queries.extend([
            {
                "query": "What is dependency injection in web frameworks?",
                "answer": "Dependency injection means the framework provides (injects) dependencies that your route handlers or views need, rather than having them construct dependencies themselves. This makes code more testable, promotes loose coupling, and centralizes configuration.",
            },
            {
                "query": "What is the difference between FastAPI and Flask?",
                "answer": "FastAPI is async-first, has built-in data validation with Pydantic, automatic API docs, and modern Python type hints. Flask is synchronous by default, more minimal, and gives you more control over structure. FastAPI is better for APIs, Flask for traditional web apps.",
            },
        ])

    # Generic Python questions
    queries.extend([
        {
            "query": "What is a decorator in Python?",
            "answer": "A decorator is a function that wraps another function to modify its behavior. It uses the @decorator syntax and is applied before the function definition. Common uses include logging, authentication, caching, and validation.",
        },
        {
            "query": "What is the difference between a list and a tuple?",
            "answer": "Lists are mutable (can be changed after creation) and use square brackets []. Tuples are immutable (cannot be changed) and use parentheses (). Tuples are faster and can be used as dictionary keys, while lists are more flexible.",
        },
    ])

    if not queries:
        return None

    selected = random.choice(queries)

    return {
        "text": format_direct_chat(
            query=selected["query"],
            answer=selected["answer"],
        ),
        "source": "stack_direct",
        "category": category,
    }


def format_chat(query: str, tool_name: str, tool_args: dict, tool_result: str, final_answer: str) -> str:
    """Format a tool-calling conversation in Qwen format."""
    # Format tool call
    tool_call = {
        "name": tool_name,
        "arguments": tool_args,
    }

    return (
        f"<|im_start|>system\n"
        f"You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"I'll use the {tool_name} tool.\n\n"
        f"```json\n"
        f"{json.dumps(tool_call, indent=2)}\n"
        f"```<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Tool result: {tool_result}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"{final_answer}<|im_end|>"
    )


def format_direct_chat(query: str, answer: str) -> str:
    """Format a direct-answer conversation in Qwen format."""
    return (
        f"<|im_start|>system\n"
        f"You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"{answer}<|im_end|>"
    )


def main():
    print("=" * 80)
    print("STACK V2 EXAMPLE GENERATOR")
    print("=" * 80)
    print("\nGenerating tool-calling examples from Stack v2 Python code")
    print()

    # Load filtered Stack v2 data
    input_file = Path("data/stack_v2/filtered_python.jsonl")
    if not input_file.exists():
        print(f"❌ Error: {input_file} not found")
        print("   Run scripts/download_stack_v2.py first")
        return

    print(f"Loading filtered files from {input_file}...")
    items = []
    with input_file.open() as f:
        for line in f:
            items.append(json.loads(line))

    print(f"✓ Loaded {len(items)} filtered files\n")

    # Generate examples
    print("Generating examples...")
    print("  Target: 300 grep, 150 read, 100 direct = 550 total")
    print()

    grep_examples = []
    read_examples = []
    direct_examples = []

    for item in items:
        # Try to generate each type (not all will succeed)
        if len(grep_examples) < 300:
            ex = generate_grep_example(item)
            if ex:
                grep_examples.append(ex)

        if len(read_examples) < 150:
            ex = generate_read_example(item)
            if ex:
                read_examples.append(ex)

        if len(direct_examples) < 100:
            ex = generate_direct_example(item)
            if ex:
                direct_examples.append(ex)

        # Progress update
        total = len(grep_examples) + len(read_examples) + len(direct_examples)
        if total % 50 == 0:
            print(f"  Generated: {total} examples "
                  f"(grep: {len(grep_examples)}, read: {len(read_examples)}, direct: {len(direct_examples)})")

        # Stop when we have enough
        if (len(grep_examples) >= 300 and
            len(read_examples) >= 150 and
            len(direct_examples) >= 100):
            break

    total_generated = len(grep_examples) + len(read_examples) + len(direct_examples)

    print("\n✓ Generation complete!")
    print(f"  Grep examples: {len(grep_examples)}")
    print(f"  Read examples: {len(read_examples)}")
    print(f"  Direct examples: {len(direct_examples)}")
    print(f"  Total: {total_generated}")

    # Combine and shuffle
    all_examples = grep_examples + read_examples + direct_examples
    random.shuffle(all_examples)

    # Save
    output_file = Path("data/stack_v2/training_examples.jsonl")
    with output_file.open('w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + '\n')

    print(f"\n✅ Saved to {output_file}")
    print(f"   {len(all_examples)} examples ready for training")

    # Show distribution
    print("\nType distribution:")
    print(f"  Tool-calling (grep + read): {len(grep_examples) + len(read_examples)} ({(len(grep_examples) + len(read_examples))/total_generated*100:.1f}%)")
    print(f"  Direct answers: {len(direct_examples)} ({len(direct_examples)/total_generated*100:.1f}%)")

    print("\nNext step: Run scripts/merge_training_data.py to combine with existing examples")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)
    main()
