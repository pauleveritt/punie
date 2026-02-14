#!/usr/bin/env python3
"""Generate tool-calling examples from cloned Python repositories.

Analyzes real code from popular projects and creates training examples:
- grep queries (find patterns, classes, functions)
- read_file queries (show implementations)
- direct answers (concepts related to the code)

Target: 500+ high-quality examples from diverse Python projects.
"""

import ast
import json
import random
from pathlib import Path


MIN_FILE_SIZE = 200  # Skip tiny files
MAX_FILE_SIZE = 10000  # Skip huge files
MIN_LINES = 10
MAX_LINES = 500


def get_python_files(repo_dir: Path) -> list[Path]:
    """Get Python files from a repository."""
    files = []

    for py_file in repo_dir.rglob("*.py"):
        # Skip common non-source directories
        parts = py_file.parts
        if any(skip in parts for skip in ["tests", "test", ".git", "venv", "__pycache__", "build", "dist"]):
            continue

        # Check size
        try:
            content = py_file.read_text()
            lines = content.splitlines()

            if len(content) < MIN_FILE_SIZE or len(content) > MAX_FILE_SIZE:
                continue
            if len(lines) < MIN_LINES or len(lines) > MAX_LINES:
                continue

            files.append(py_file)
        except (OSError, UnicodeDecodeError):
            continue

    return files


def extract_ast_info(code: str) -> dict:
    """Extract information from Python code using AST."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}

    info = {
        "classes": [],
        "functions": [],
        "imports": [],
        "decorators": [],
        "has_async": False,
        "has_type_hints": False,
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            info["classes"].append({
                "name": node.name,
                "bases": [ast.unparse(base) for base in node.bases],
                "decorators": [ast.unparse(dec) for dec in node.decorator_list],
            })

        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            if is_async:
                info["has_async"] = True

            info["functions"].append({
                "name": node.name,
                "is_async": is_async,
                "decorators": [ast.unparse(dec) for dec in node.decorator_list],
                "has_return_annotation": node.returns is not None,
            })

            # Check for type hints
            if node.returns or any(arg.annotation for arg in node.args.args):
                info["has_type_hints"] = True

        elif isinstance(node, ast.Import):
            for alias in node.names:
                info["imports"].append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                info["imports"].append(node.module)

    return info


def generate_grep_examples(file_path: Path, code: str, ast_info: dict, category: str) -> list[dict]:
    """Generate grep/search examples from code."""
    examples = []
    rel_path = str(file_path).replace(str(Path.cwd()), "")

    # Find classes
    if ast_info.get("classes"):
        cls = random.choice(ast_info["classes"])
        examples.append({
            "query": f"Find all classes named {cls['name']}",
            "tool": "run_command",
            "args": {"command": f"grep -r 'class {cls['name']}' --include='*.py'"},
            "result": f"{rel_path}: class {cls['name']}:",
            "answer": f"Found class {cls['name']} in {rel_path}.",
        })

        # Base classes
        if cls["bases"]:
            base = cls["bases"][0]
            examples.append({
                "query": f"Find all classes that inherit from {base}",
                "tool": "run_command",
                "args": {"command": f"grep -r 'class.*{base}' --include='*.py'"},
                "result": f"{rel_path}: class {cls['name']}({base}):",
                "answer": f"Found class {cls['name']} inheriting from {base} in {rel_path}.",
            })

    # Find functions
    if ast_info.get("functions"):
        func = random.choice(ast_info["functions"])
        examples.append({
            "query": f"Find the {func['name']} function",
            "tool": "run_command",
            "args": {"command": f"grep -r 'def {func['name']}' --include='*.py'"},
            "result": f"{rel_path}: def {func['name']}(",
            "answer": f"Found {func['name']} function in {rel_path}.",
        })

        # Async functions
        if func["is_async"]:
            examples.append({
                "query": "Find all async functions in this codebase",
                "tool": "run_command",
                "args": {"command": "grep -r 'async def' --include='*.py'"},
                "result": f"{rel_path}: async def {func['name']}(",
                "answer": f"Found async function {func['name']} in {rel_path}.",
            })

    # Find imports
    if ast_info.get("imports"):
        imp = random.choice(ast_info["imports"])
        examples.append({
            "query": f"Find all files that import {imp}",
            "tool": "run_command",
            "args": {"command": f"grep -r 'import {imp}' --include='*.py'"},
            "result": f"{rel_path}: import {imp}",
            "answer": f"Found import of {imp} in {rel_path}.",
        })

    # Decorators
    if ast_info.get("functions"):
        decorated = [f for f in ast_info["functions"] if f["decorators"]]
        if decorated:
            func = random.choice(decorated)
            dec = func["decorators"][0]
            examples.append({
                "query": f"Find all uses of the {dec} decorator",
                "tool": "run_command",
                "args": {"command": f"grep -r '{dec}' --include='*.py'"},
                "result": f"{rel_path}: {dec}",
                "answer": f"Found {dec} decorator on {func['name']} in {rel_path}.",
            })

    return examples


def generate_read_examples(file_path: Path, code: str, ast_info: dict, category: str) -> list[dict]:
    """Generate read_file examples from code."""
    examples = []
    rel_path = str(file_path).replace(str(Path.cwd()), "")

    # Read file with class
    if ast_info.get("classes"):
        cls = random.choice(ast_info["classes"])
        snippet = code[:300]
        examples.append({
            "query": f"Show me the {cls['name']} class implementation",
            "tool": "read_file",
            "args": {"path": rel_path},
            "result": snippet + "\n...",
            "answer": f"Here's the {cls['name']} class from {rel_path}. "
                     f"It has {len([m for m in ast_info.get('functions', []) if m['name'].startswith('_')])} methods.",
        })

    # Read file with function
    if ast_info.get("functions"):
        func = random.choice(ast_info["functions"])
        snippet = code[:300]
        examples.append({
            "query": f"Show me how {func['name']} is implemented",
            "tool": "read_file",
            "args": {"path": rel_path},
            "result": snippet + "\n...",
            "answer": f"Here's the implementation from {rel_path}. "
                     f"The function is {'async' if func['is_async'] else 'sync'}.",
        })

    return examples


def generate_direct_examples(file_path: Path, code: str, ast_info: dict, category: str) -> list[dict]:
    """Generate direct-answer examples based on code features."""
    examples = []

    # Concept questions based on category
    if category == "web":
        examples.extend([
            {
                "query": "What is dependency injection in web frameworks?",
                "answer": "Dependency injection means the framework provides (injects) dependencies that your "
                         "route handlers or views need, rather than having them construct dependencies themselves. "
                         "This makes code more testable, promotes loose coupling, and centralizes configuration.",
            },
            {
                "query": "What is the difference between sync and async routes?",
                "answer": "Sync routes block the worker thread while processing, suitable for CPU-bound work. "
                         "Async routes can yield control while waiting for I/O (database, external APIs), "
                         "allowing the server to handle more concurrent requests.",
            },
        ])

    elif category == "testing":
        examples.extend([
            {
                "query": "What are fixtures in pytest?",
                "answer": "Fixtures are reusable components that provide setup/teardown logic for tests. "
                         "They can inject dependencies into test functions via arguments, manage resources "
                         "(database connections, temp files), and have flexible scopes (function, class, module, session).",
            },
            {
                "query": "When should I use parametrize?",
                "answer": "Use @pytest.mark.parametrize when you want to run the same test logic with different "
                         "input values. It's cleaner than writing multiple similar test functions and makes it "
                         "easy to add more test cases by just adding to the parameter list.",
            },
        ])

    elif category == "cli":
        examples.extend([
            {
                "query": "What is the difference between argparse and click?",
                "answer": "Argparse is Python's built-in CLI parser with imperative setup. Click uses decorators "
                         "for declarative command definition, has better nesting/grouping, automatic help generation, "
                         "and more intuitive parameter handling. Click is more modern and easier to use.",
            },
            {
                "query": "What are command groups?",
                "answer": "Command groups allow you to organize related commands under a parent command, like 'git commit' "
                         "and 'git push' are both under 'git'. This helps structure complex CLI tools with many commands.",
            },
        ])

    elif category == "async":
        examples.extend([
            {
                "query": "What is the difference between asyncio and threading?",
                "answer": "Asyncio uses cooperative multitasking - tasks explicitly yield control with 'await'. "
                         "Threading uses preemptive multitasking - the OS switches between threads. Asyncio is "
                         "better for I/O-bound work, threading for CPU-bound work that releases the GIL.",
            },
            {
                "query": "When should I use async/await?",
                "answer": "Use async/await when your code does lots of I/O operations (network, file, database) "
                         "where tasks spend time waiting. It's most beneficial for I/O-bound applications like "
                         "web servers, API clients, or database applications with many concurrent operations.",
            },
        ])

    elif category == "typing":
        examples.extend([
            {
                "query": "What is the difference between Protocol and ABC?",
                "answer": "Protocol enables structural subtyping (duck typing) - any class that implements the "
                         "required methods automatically satisfies the protocol. ABC (Abstract Base Class) uses "
                         "nominal subtyping - classes must explicitly inherit. Protocol is more flexible and Pythonic.",
            },
            {
                "query": "What are generic types?",
                "answer": "Generic types allow you to write flexible code that works with multiple types while "
                         "maintaining type safety. For example, List[T] can be List[int] or List[str]. "
                         "You define generics with TypeVar and use them in class/function signatures.",
            },
        ])

    # Universal Python questions (always add a few)
    examples.extend([
        {
            "query": "What is a decorator?",
            "answer": "A decorator is a function that wraps another function to modify its behavior. "
                     "It uses the @decorator syntax and is applied before the function definition. "
                     "Common uses include logging, authentication, caching, and validation.",
        },
        {
            "query": "What is the difference between staticmethod and classmethod?",
            "answer": "staticmethod is just a regular function in a class namespace - no special first parameter. "
                     "classmethod receives the class (cls) as first parameter, useful for alternative constructors. "
                     "Regular methods receive the instance (self).",
        },
    ])

    return examples


def format_tool_example(ex: dict) -> str:
    """Format a tool-calling example in Qwen chat format."""
    tool_call = {"name": ex["tool"], "arguments": ex["args"]}

    return (
        f"<|im_start|>system\n"
        f"You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{ex['query']}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"I'll use the {ex['tool']} tool.\n\n"
        f"```json\n"
        f"{json.dumps(tool_call, indent=2)}\n"
        f"```<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Tool result: {ex['result']}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"{ex['answer']}<|im_end|>"
    )


def format_direct_example(ex: dict) -> str:
    """Format a direct-answer example in Qwen chat format."""
    return (
        f"<|im_start|>system\n"
        f"You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{ex['query']}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"{ex['answer']}<|im_end|>"
    )


def main():
    print("=" * 80)
    print("REPOSITORY EXAMPLE GENERATOR")
    print("=" * 80)
    print("\nGenerating training examples from cloned repositories")
    print()

    repos_dir = Path("data/repos")
    if not repos_dir.exists():
        print(f"❌ Error: {repos_dir} not found")
        print("   Run scripts/clone_popular_repos.py first")
        return

    # Get repo info
    repos = [
        {"name": "fastapi", "category": "web"},
        {"name": "flask", "category": "web"},
        {"name": "pytest", "category": "testing"},
        {"name": "typer", "category": "cli"},
        {"name": "click", "category": "cli"},
        {"name": "httpx", "category": "async"},
        {"name": "starlette", "category": "async"},
        {"name": "pydantic", "category": "typing"},
        {"name": "attrs", "category": "typing"},
        {"name": "structlog", "category": "tools"},
    ]

    all_grep_examples = []
    all_read_examples = []
    all_direct_examples = []

    print("Processing repositories...")
    for repo in repos:
        repo_path = repos_dir / repo["name"]
        if not repo_path.exists():
            print(f"  ⚠️  Skipping {repo['name']} (not found)")
            continue

        print(f"\n  {repo['name']} ({repo['category']}):")

        # Get Python files
        py_files = get_python_files(repo_path)
        print(f"    Found {len(py_files)} Python files")

        # Sample files (don't process all)
        sample_files = random.sample(py_files, min(20, len(py_files)))

        for py_file in sample_files:
            try:
                code = py_file.read_text()
                ast_info = extract_ast_info(code)

                # Generate examples
                grep_exs = generate_grep_examples(py_file, code, ast_info, repo["category"])
                read_exs = generate_read_examples(py_file, code, ast_info, repo["category"])
                direct_exs = generate_direct_examples(py_file, code, ast_info, repo["category"])

                all_grep_examples.extend(grep_exs)
                all_read_examples.extend(read_exs)
                all_direct_examples.extend(direct_exs)

            except Exception as e:
                print(f"      Error processing {py_file.name}: {e}")
                continue

        print(f"    Generated: {len(all_grep_examples)} grep, "
              f"{len(all_read_examples)} read, {len(all_direct_examples)} direct")

    print(f"\n{'=' * 80}")
    print("GENERATION COMPLETE")
    print("=" * 80)
    print(f"  Grep examples: {len(all_grep_examples)}")
    print(f"  Read examples: {len(all_read_examples)}")
    print(f"  Direct examples: {len(all_direct_examples)}")
    print(f"  Total: {len(all_grep_examples) + len(all_read_examples) + len(all_direct_examples)}")

    # Sample and format
    target_grep = min(300, len(all_grep_examples))
    target_read = min(150, len(all_read_examples))
    target_direct = min(100, len(all_direct_examples))

    sampled_grep = random.sample(all_grep_examples, target_grep)
    sampled_read = random.sample(all_read_examples, target_read)
    sampled_direct = random.sample(all_direct_examples, target_direct)

    # Format and save
    output_dir = Path("data/repos_examples")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "training_examples.jsonl"

    all_formatted = []

    for ex in sampled_grep:
        all_formatted.append({
            "text": format_tool_example(ex),
            "source": "repo_grep",
        })

    for ex in sampled_read:
        all_formatted.append({
            "text": format_tool_example(ex),
            "source": "repo_read",
        })

    for ex in sampled_direct:
        all_formatted.append({
            "text": format_direct_example(ex),
            "source": "repo_direct",
        })

    random.shuffle(all_formatted)

    with output_file.open('w') as f:
        for ex in all_formatted:
            f.write(json.dumps(ex) + '\n')

    print(f"\n✅ Saved {len(all_formatted)} examples to {output_file}")
    print(f"   Tool-calling: {target_grep + target_read} ({(target_grep + target_read)/len(all_formatted)*100:.1f}%)")
    print(f"   Direct answers: {target_direct} ({target_direct/len(all_formatted)*100:.1f}%)")
    print()
    print("Next step: Run scripts/merge_training_data.py")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)
    main()
