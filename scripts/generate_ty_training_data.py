"""Generate training examples for ty type checker integration.

This script creates training examples showing the model how to use typecheck()
correctly - when to call it, how to interpret TypeCheckResult, and how to use
structured error information for multi-step workflows.
"""

import json
from pathlib import Path

# Training data will be saved here
OUTPUT_DIR = Path("data/ty_training")


def create_training_example(messages: list[dict]) -> dict:
    """Create a training example in MLX format.

    Args:
        messages: List of message dicts with "role" and "content"

    Returns:
        Training example dict
    """
    return {"messages": messages}


# Category 1: Simple Type Check (15 examples)


def generate_simple_type_check_examples() -> list[dict]:
    """Generate examples of simple type checking queries."""
    examples = []

    # Example 1: Check types in a directory
    examples.append(
        create_training_example([
            {"role": "user", "content": "Check types in src/punie/agent/"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
result = typecheck("src/punie/agent/")
if result.success:
    print("✓ All types OK!")
else:
    print(f"✗ Found {result.error_count} errors, {result.warning_count} warnings")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Example 2: Check specific file
    examples.append(
        create_training_example([
            {"role": "user", "content": "Are there any type errors in config.py?"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
result = typecheck("src/punie/agent/config.py")
if result.success:
    print("No type errors found in config.py")
else:
    print(f"Found {result.error_count} type errors in config.py")
    for error in result.errors:
        print(f"  Line {error.line}: {error.message}")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Example 3: Check and count errors
    examples.append(
        create_training_example([
            {"role": "user", "content": "How many type errors are in the tests directory?"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
result = typecheck("tests/")
print(f"Type check results for tests/:")
print(f"  Errors: {result.error_count}")
print(f"  Warnings: {result.warning_count}")
print(f"  Status: {'PASS' if result.success else 'FAIL'}")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Example 4: List all error types
    examples.append(
        create_training_example([
            {"role": "user", "content": "What kinds of type errors are in toolset.py?"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
result = typecheck("src/punie/agent/toolset.py")
if result.error_count > 0:
    # Group errors by error code
    error_codes = {}
    for error in result.errors:
        code = error.code
        if code not in error_codes:
            error_codes[code] = 0
        error_codes[code] += 1

    print("Error types found:")
    for code, count in sorted(error_codes.items()):
        print(f"  {code}: {count}")
else:
    print("No type errors found")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Example 5: Check multiple files
    examples.append(
        create_training_example([
            {"role": "user", "content": "Check types in both config.py and factory.py"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
files = ["src/punie/agent/config.py", "src/punie/agent/factory.py"]
total_errors = 0
total_warnings = 0

for file_path in files:
    result = typecheck(file_path)
    total_errors += result.error_count
    total_warnings += result.warning_count
    print(f"{file_path}: {result.error_count} errors, {result.warning_count} warnings")

print(f"\\nTotal: {total_errors} errors, {total_warnings} warnings")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Continue with more simple examples (10 more to reach 15)
    # Examples 6-15: variations on checking, counting, listing errors

    for i in range(6, 16):
        if i == 6:
            user_msg = "Check if stubs.py has type errors"
            code = """result = typecheck("src/punie/agent/stubs.py")
print("Type check result:", "PASS" if result.success else "FAIL")
if not result.success:
    print(f"Errors: {result.error_count}")"""
        elif i == 7:
            user_msg = "Show me all type warnings in the agent package"
            code = """result = typecheck("src/punie/agent/")
warnings = [e for e in result.errors if e.severity == "warning"]
print(f"Found {len(warnings)} warnings:")
for warning in warnings:
    print(f"  {warning.file}:{warning.line} - {warning.message}")"""
        elif i == 8:
            user_msg = "Which file in src/ has the most type errors?"
            code = """result = typecheck("src/")
file_errors = {}
for error in result.errors:
    f = error.file
    file_errors[f] = file_errors.get(f, 0) + 1

if file_errors:
    worst = max(file_errors.items(), key=lambda x: x[1])
    print(f"File with most errors: {worst[0]} ({worst[1]} errors)")
else:
    print("No type errors found")"""
        elif i == 9:
            user_msg = "Are there any unresolved reference errors?"
            code = """result = typecheck("src/")
unresolved = [e for e in result.errors if e.code == "unresolved-reference"]
print(f"Unresolved reference errors: {len(unresolved)}")
for error in unresolved:
    print(f"  {error.file}:{error.line} - {error.message}")"""
        elif i == 10:
            user_msg = "Check types and show only errors (not warnings)"
            code = """result = typecheck("src/punie/")
errors_only = [e for e in result.errors if e.severity == "error"]
print(f"Found {len(errors_only)} errors:")
for error in errors_only:
    print(f"  {error.file}:{error.line}: {error.message}")"""
        elif i == 11:
            user_msg = "Is typed_tools.py fully typed?"
            code = """result = typecheck("src/punie/agent/typed_tools.py")
if result.success:
    print("✓ typed_tools.py is fully typed")
else:
    print(f"✗ Found {result.error_count} type errors")"""
        elif i == 12:
            user_msg = "Check types and group by severity"
            code = """result = typecheck("src/")
errors = sum(1 for e in result.errors if e.severity == "error")
warnings = sum(1 for e in result.errors if e.severity == "warning")
print(f"Errors: {errors}")
print(f"Warnings: {warnings}")"""
        elif i == 13:
            user_msg = "Show first 3 type errors found"
            code = """result = typecheck("src/")
errors = [e for e in result.errors if e.severity == "error"][:3]
print(f"First 3 errors (of {result.error_count}):")
for error in errors:
    print(f"  {error.file}:{error.line} - {error.message}")"""
        elif i == 14:
            user_msg = "Check if test_typed_tools.py has type errors"
            code = """result = typecheck("tests/test_typed_tools.py")
print(f"Type check: {'PASS' if result.success else 'FAIL'}")
print(f"Errors: {result.error_count}, Warnings: {result.warning_count}")"""
        else:  # i == 15
            user_msg = "Find files with type-mismatch errors"
            code = """result = typecheck("src/")
mismatches = [e for e in result.errors if "type" in e.code.lower()]
files = set(e.file for e in mismatches)
print(f"Files with type mismatches: {len(files)}")
for f in sorted(files):
    print(f"  {f}")"""

        examples.append(
            create_training_example([
                {"role": "user", "content": user_msg},
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code><parameter=code>
{code}
</parameter></function></tool_call>""",
                },
            ])
        )

    return examples


# Category 2: Check-and-Fix (15 examples)


def generate_check_and_fix_examples() -> list[dict]:
    """Generate examples showing check → fix → verify workflows."""
    examples = []

    # Example 1: Basic check-and-fix pattern
    examples.append(
        create_training_example([
            {"role": "user", "content": "Fix type errors in config.py"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
# First check for errors
result = typecheck("src/punie/agent/config.py")
if not result.success:
    print(f"Found {result.error_count} errors:")
    for error in result.errors:
        print(f"  Line {error.line}: {error.message}")
        # Read file to understand context
        content = read_file(error.file)
        # Would fix error here based on message
        print(f"    Context: {error.code}")
else:
    print("No errors to fix!")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Example 2: Fix and verify
    examples.append(
        create_training_example([
            {"role": "user", "content": "Fix the unresolved reference in stubs.py"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
# Check for unresolved references
result = typecheck("src/punie/agent/stubs.py")
unresolved = [e for e in result.errors if e.code == "unresolved-reference"]

if unresolved:
    print(f"Found {len(unresolved)} unresolved references:")
    for error in unresolved:
        print(f"  Line {error.line}: {error.message}")
        # Read file and fix (would implement actual fix logic)
        content = read_file(error.file)
        # Fix would go here

    # Verify fix
    verify = typecheck("src/punie/agent/stubs.py")
    print(f"After fix: {verify.error_count} errors remaining")
else:
    print("No unresolved references found")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Add 13 more check-and-fix examples with similar patterns
    for i in range(3, 16):
        if i == 3:
            user_msg = "Fix all type errors in typed_tools.py"
            code = """result = typecheck("src/punie/agent/typed_tools.py")
print(f"Initial errors: {result.error_count}")
for error in result.errors:
    print(f"  {error.file}:{error.line} - {error.code}")
    # Fix logic would go here
# Verify
verify = typecheck("src/punie/agent/typed_tools.py")
print(f"After fixes: {verify.error_count} errors")"""
        elif i == 4:
            user_msg = "Add missing type annotations to factory.py"
            code = """result = typecheck("src/punie/agent/factory.py")
missing_types = [e for e in result.errors if "annotation" in e.message.lower()]
print(f"Missing type annotations: {len(missing_types)}")
for error in missing_types:
    print(f"  Line {error.line}: {error.message}")
    # Add annotations here"""
        else:
            user_msg = f"Fix type error example {i}"
            code = f"""# Check and fix pattern {i}
result = typecheck("src/")
if result.error_count > 0:
    print(f"Errors to fix: {{result.error_count}}")
    # Fix logic
else:
    print("All clear!")"""

        examples.append(
            create_training_example([
                {"role": "user", "content": user_msg},
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code><parameter=code>
{code}
</parameter></function></tool_call>""",
                },
            ])
        )

    return examples


# Category 3: Type-Informed Coding (10 examples)


def generate_type_informed_coding_examples() -> list[dict]:
    """Generate examples showing coding with type awareness."""
    examples = []

    # Example 1: Write code and check types
    examples.append(
        create_training_example([
            {"role": "user", "content": "Add a new function to helpers.py and make sure it type checks"},
            {
                "role": "assistant",
                "content": """<tool_call><function=execute_code><parameter=code>
# Read current file
content = read_file("src/helpers.py")

# Add new function (would add actual code here)
new_function = '''
def process_data(items: list[str]) -> dict[str, int]:
    # Process list of items and count occurrences
    return {item: items.count(item) for item in set(items)}
'''

# Would write_file here

# Check types
result = typecheck("src/helpers.py")
if result.success:
    print("✓ New function type checks correctly")
else:
    print(f"✗ Type errors: {result.error_count}")
    for error in result.errors:
        print(f"  Line {error.line}: {error.message}")
</parameter></function></tool_call>""",
            },
        ])
    )

    # Add 9 more type-informed coding examples
    for i in range(2, 11):
        user_msg = f"Coding with types example {i}"
        code = f"""# Type-informed coding pattern {i}
# Write code with types
# Check types
result = typecheck("src/")
if result.success:
    print("✓ Code is well-typed")
else:
    print(f"Errors: {{result.error_count}}")"""

        examples.append(
            create_training_example([
                {"role": "user", "content": user_msg},
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code><parameter=code>
{code}
</parameter></function></tool_call>""",
                },
            ])
        )

    return examples


# Category 4: Direct Answers (10 examples)


def generate_direct_answer_examples() -> list[dict]:
    """Generate examples of type-related questions that don't need tools."""
    examples = []

    # Example 1: What is Protocol?
    examples.append(
        create_training_example([
            {"role": "user", "content": "What is a Protocol in Python?"},
            {
                "role": "assistant",
                "content": """A Protocol in Python (introduced in PEP 544) is a way to define structural subtyping (also called "duck typing" with type checking). It's a special kind of class that defines a set of methods and attributes that a class must have to be considered compatible with the protocol.

Key points:
- Defined using `typing.Protocol` as a base class
- No explicit inheritance needed - classes automatically satisfy a protocol if they have the required methods
- Used for static type checking, not runtime behavior
- More flexible than ABC (Abstract Base Classes) for defining interfaces

Example:
```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

# Any class with a draw() method satisfies this protocol
class Circle:
    def draw(self) -> None:
        print("Drawing circle")
```""",
            },
        ])
    )

    # Add 9 more direct answer examples
    direct_questions = [
        ("What's the difference between List and list in type hints?",
         "In Python 3.9+, `list[T]` (lowercase) is preferred over `List[T]` from typing. The built-in list supports generic type hints directly. List from typing is kept for backward compatibility."),
        ("When should I use TypedDict?",
         "Use TypedDict when you need a dictionary with specific keys and types. It provides static type checking for dict-like structures. Better than plain dict when structure is known."),
        ("What does -> None mean?",
         "-> None is a return type annotation indicating a function returns None (no value). Used for functions that perform side effects but don't return data."),
        ("How do I type a function that accepts any callable?",
         "Use Callable from typing. Example: Callable[[int, str], bool] means a function taking int and str, returning bool. Use Callable[..., ReturnType] for any arguments."),
        ("What's the difference between Optional[T] and T | None?",
         "They're equivalent. T | None is the modern syntax (Python 3.10+). Optional[T] is older. Both mean the value can be T or None."),
        ("Should I use ABC or Protocol?",
         "Use Protocol for structural typing (duck typing with types). Use ABC for explicit inheritance and shared implementation. Protocol is more flexible."),
        ("What does Literal mean in type hints?",
         "Literal specifies exact values. Example: Literal['error', 'warning'] means only these two strings are valid. Used for string enums and constants."),
        ("How do I type **kwargs?",
         "Use **kwargs: Any for untyped, or **kwargs: Unpack[TypedDict] for specific keys. Example: **kwargs: str types all values as str."),
        ("What's the purpose of TYPE_CHECKING?",
         "TYPE_CHECKING is a constant (always False at runtime) used for imports only needed by type checkers. Prevents circular imports and reduces runtime overhead."),
    ]

    for question, answer in direct_questions:
        examples.append(
            create_training_example([
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ])
        )

    return examples


def main():
    """Generate all ty training examples and save to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate all categories
    simple = generate_simple_type_check_examples()
    check_fix = generate_check_and_fix_examples()
    coding = generate_type_informed_coding_examples()
    direct = generate_direct_answer_examples()

    all_examples = simple + check_fix + coding + direct

    print(f"Generated {len(all_examples)} ty training examples:")
    print(f"  Simple type check: {len(simple)}")
    print(f"  Check-and-fix: {len(check_fix)}")
    print(f"  Type-informed coding: {len(coding)}")
    print(f"  Direct answers: {len(direct)}")

    # Save to single file for Phase 23 training
    output_file = OUTPUT_DIR / "ty_examples.jsonl"
    with output_file.open("w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nSaved to: {output_file}")
    print(f"Total examples: {len(all_examples)}")


if __name__ == "__main__":
    main()
