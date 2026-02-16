#!/usr/bin/env python
"""Generate training examples for LSP navigation tools (Phase 26).

Creates ~70 examples across 5 categories:
1. Simple goto_definition (15)
2. Simple find_references (15)
3. Navigation + field access (15)
4. Multi-step workflows (15)
5. Direct answers (10)

Output: data/phase26_lsp_navigation/ in JSONL format
"""

import json
from pathlib import Path


def create_message(role: str, content: str) -> dict:
    """Create a message dict for training data."""
    return {"role": role, "content": content}


def create_example(user_content: str, assistant_content: str) -> dict:
    """Create a training example with user/assistant messages."""
    return {
        "messages": [
            create_message("user", user_content),
            create_message("assistant", assistant_content),
        ]
    }


def generate_simple_goto_definition() -> list[dict]:
    """Generate simple goto_definition examples (15)."""
    examples = []

    # Example 1: Find class definition
    examples.append(
        create_example(
            "Where is the UserService class defined?",
            """<tool_call>result = goto_definition("src/services/user.py", 45, 20, "UserService")
if result.success:
    loc = result.locations[0]
    print(f"UserService is defined at {loc.file}:{loc.line}:{loc.column}")
else:
    print("Definition not found")</tool_call>""",
        )
    )

    # Example 2: Find function definition
    examples.append(
        create_example(
            "Where is process_order defined in the codebase?",
            """<tool_call>result = goto_definition("src/api/orders.py", 120, 15, "process_order")
if result.success:
    print(f"Found definition at {result.locations[0].file}:{result.locations[0].line}")
else:
    print("Could not find definition")</tool_call>""",
        )
    )

    # Example 3: Find method definition
    examples.append(
        create_example(
            "Find where the calculate_total method is defined",
            """<tool_call>result = goto_definition("src/models/order.py", 85, 12, "calculate_total")
if result.success:
    loc = result.locations[0]
    print(f"Method defined in {loc.file} at line {loc.line}")
</tool_call>""",
        )
    )

    # Example 4: Find variable definition
    examples.append(
        create_example(
            "Where is DATABASE_URL defined?",
            """<tool_call>result = goto_definition("src/config.py", 10, 5, "DATABASE_URL")
if result.success:
    print(f"DATABASE_URL defined at {result.locations[0].file}:{result.locations[0].line}")
</tool_call>""",
        )
    )

    # Example 5: Find BaseModel import
    examples.append(
        create_example(
            "Where does BaseModel come from in typed_tools.py?",
            """<tool_call>result = goto_definition("src/punie/agent/typed_tools.py", 13, 25, "BaseModel")
if result.success:
    loc = result.locations[0]
    print(f"BaseModel is defined in {loc.file}")
    print(f"Location: line {loc.line}, column {loc.column}")
</tool_call>""",
        )
    )

    # Example 6: Check if definition exists
    examples.append(
        create_example(
            "Is UserRepository defined in the project?",
            """<tool_call>result = goto_definition("src/services/user.py", 30, 15, "UserRepository")
if result.success:
    print(f"Yes, UserRepository is defined at {result.locations[0].file}:{result.locations[0].line}")
else:
    print("No, UserRepository is not defined")</tool_call>""",
        )
    )

    # Example 7: Find type alias
    examples.append(
        create_example(
            "Where is the OrderStatus type defined?",
            """<tool_call>result = goto_definition("src/models/order.py", 25, 18, "OrderStatus")
if result.success:
    print(f"OrderStatus type defined at {result.locations[0].file}:{result.locations[0].line}")
</tool_call>""",
        )
    )

    # Example 8: Multiple definitions
    examples.append(
        create_example(
            "Find all definitions of process in the codebase",
            """<tool_call>result = goto_definition("src/api/main.py", 55, 10, "process")
if result.success:
    print(f"Found {len(result.locations)} definitions:")
    for loc in result.locations:
        print(f"  - {loc.file}:{loc.line}")
</tool_call>""",
        )
    )

    # Example 9: Imported symbol
    examples.append(
        create_example(
            "Where is TypeCheckResult originally defined?",
            """<tool_call>result = goto_definition("src/punie/agent/toolset.py", 324, 35, "TypeCheckResult")
if result.success:
    print(f"TypeCheckResult defined in {result.locations[0].file} at line {result.locations[0].line}")
</tool_call>""",
        )
    )

    # Example 10: Class attribute
    examples.append(
        create_example(
            "Find the definition of the error_count field",
            """<tool_call>result = goto_definition("src/punie/agent/typed_tools.py", 98, 25, "error_count")
if result.success:
    loc = result.locations[0]
    print(f"error_count field defined at line {loc.line} in {loc.file}")
</tool_call>""",
        )
    )

    # Example 11: Decorator
    examples.append(
        create_example(
            "Where is the @dataclass decorator defined?",
            """<tool_call>result = goto_definition("src/punie/agent/config.py", 66, 2, "dataclass")
if result.success:
    print(f"dataclass is from {result.locations[0].file}")
</tool_call>""",
        )
    )

    # Example 12: Exception class
    examples.append(
        create_example(
            "Find where CodeExecutionError is defined",
            """<tool_call>result = goto_definition("src/punie/agent/monty_runner.py", 164, 15, "CodeExecutionError")
if result.success:
    print(f"CodeExecutionError defined at {result.locations[0].file}:{result.locations[0].line}")
</tool_call>""",
        )
    )

    # Example 13: Enum value
    examples.append(
        create_example(
            "Where is the PENDING status value defined?",
            """<tool_call>result = goto_definition("src/models/status.py", 42, 20, "PENDING")
if result.success:
    print(f"PENDING defined in {result.locations[0].file} at line {result.locations[0].line}")
</tool_call>""",
        )
    )

    # Example 14: Generic type parameter
    examples.append(
        create_example(
            "Find the definition of the T type parameter",
            """<tool_call>result = goto_definition("src/utils/generics.py", 15, 25, "T")
if result.success:
    print(f"Type parameter T defined at line {result.locations[0].line}")
</tool_call>""",
        )
    )

    # Example 15: Constant
    examples.append(
        create_example(
            "Where is MAX_RETRIES defined?",
            """<tool_call>result = goto_definition("src/config.py", 35, 12, "MAX_RETRIES")
if result.success:
    print(f"MAX_RETRIES is defined at {result.locations[0].file}:{result.locations[0].line}")
</tool_call>""",
        )
    )

    return examples


def generate_simple_find_references() -> list[dict]:
    """Generate simple find_references examples (15)."""
    examples = []

    # Example 1: Find all usages of a function
    examples.append(
        create_example(
            "Where is parse_ty_output used in the codebase?",
            """<tool_call>result = find_references("src/punie/agent/typed_tools.py", 54, 9, "parse_ty_output")
if result.success:
    print(f"Found {result.reference_count} references:")
    for ref in result.references:
        print(f"  {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 2: Find usages of a class
    examples.append(
        create_example(
            "Show me all places where UserService is used",
            """<tool_call>result = find_references("src/services/user.py", 20, 7, "UserService")
print(f"UserService is used in {result.reference_count} locations:")
for ref in result.references:
    print(f"  - {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 3: Count references
    examples.append(
        create_example(
            "How many times is calculate_total called?",
            """<tool_call>result = find_references("src/models/order.py", 85, 12, "calculate_total")
if result.success:
    print(f"calculate_total is called {result.reference_count} times")
else:
    print("No references found")</tool_call>""",
        )
    )

    # Example 4: Check if unused
    examples.append(
        create_example(
            "Is the old_process_payment function still being used?",
            """<tool_call>result = find_references("src/services/payment.py", 150, 8, "old_process_payment")
if result.reference_count == 0:
    print("old_process_payment is not used anywhere - safe to remove")
else:
    print(f"Still used in {result.reference_count} places")
</tool_call>""",
        )
    )

    # Example 5: Group by file
    examples.append(
        create_example(
            "Which files reference TypeCheckResult?",
            """<tool_call>result = find_references("src/punie/agent/typed_tools.py", 36, 10, "TypeCheckResult")
if result.success:
    files = set(ref.file for ref in result.references)
    print(f"TypeCheckResult is referenced in {len(files)} files:")
    for file in sorted(files):
        print(f"  - {file}")
</tool_call>""",
        )
    )

    # Example 6: Find test usages
    examples.append(
        create_example(
            "Where is process_order tested?",
            """<tool_call>result = find_references("src/api/orders.py", 120, 15, "process_order")
if result.success:
    test_refs = [ref for ref in result.references if "test" in ref.file]
    print(f"process_order is tested in {len(test_refs)} test files:")
    for ref in test_refs:
        print(f"  {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 7: Check import usage
    examples.append(
        create_example(
            "Is BaseModel imported anywhere in our code?",
            """<tool_call>result = find_references("src/punie/agent/typed_tools.py", 13, 25, "BaseModel")
print(f"BaseModel is imported in {result.reference_count} places")
</tool_call>""",
        )
    )

    # Example 8: Find method calls
    examples.append(
        create_example(
            "Show all calls to the validate method",
            """<tool_call>result = find_references("src/models/base.py", 45, 10, "validate")
if result.success:
    for i, ref in enumerate(result.references[:5], 1):
        print(f"{i}. {ref.file}:{ref.line}")
    if result.reference_count > 5:
        print(f"... and {result.reference_count - 5} more")
</tool_call>""",
        )
    )

    # Example 9: Configuration value usage
    examples.append(
        create_example(
            "Where is DATABASE_URL read from config?",
            """<tool_call>result = find_references("src/config.py", 10, 5, "DATABASE_URL")
print(f"DATABASE_URL is used in {result.reference_count} locations:")
for ref in result.references:
    print(f"  {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 10: Exception usage
    examples.append(
        create_example(
            "Find all places that raise ValidationError",
            """<tool_call>result = find_references("src/models/validation.py", 15, 10, "ValidationError")
if result.success:
    print(f"ValidationError is raised in {result.reference_count} places")
</tool_call>""",
        )
    )

    # Example 11: Type usage
    examples.append(
        create_example(
            "Which functions return OrderStatus?",
            """<tool_call>result = find_references("src/models/order.py", 25, 18, "OrderStatus")
if result.success:
    print(f"OrderStatus is used as return type in {result.reference_count} functions:")
    for ref in result.references:
        print(f"  {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 12: Decorator usage
    examples.append(
        create_example(
            "Find all functions decorated with @cache",
            """<tool_call>result = find_references("src/utils/decorators.py", 20, 5, "cache")
print(f"@cache decorator is used on {result.reference_count} functions")
</tool_call>""",
        )
    )

    # Example 13: No references found
    examples.append(
        create_example(
            "Is unused_helper_function referenced anywhere?",
            """<tool_call>result = find_references("src/utils/helpers.py", 200, 8, "unused_helper_function")
if not result.success or result.reference_count == 0:
    print("unused_helper_function has no references - can be removed")
</tool_call>""",
        )
    )

    # Example 14: API endpoint usage
    examples.append(
        create_example(
            "Where is the /api/users endpoint handler used?",
            """<tool_call>result = find_references("src/api/routes.py", 55, 15, "get_users")
if result.success:
    print(f"get_users handler referenced {result.reference_count} times:")
    for ref in result.references:
        print(f"  {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 15: Count non-test references
    examples.append(
        create_example(
            "How many production usages of parse_ruff_output are there?",
            """<tool_call>result = find_references("src/punie/agent/typed_tools.py", 156, 9, "parse_ruff_output")
if result.success:
    prod_refs = [ref for ref in result.references if "test" not in ref.file]
    print(f"parse_ruff_output has {len(prod_refs)} production references")
</tool_call>""",
        )
    )

    return examples


def generate_navigation_with_field_access() -> list[dict]:
    """Generate navigation + field access examples (15)."""
    examples = []

    # Example 1: goto_definition then read file
    examples.append(
        create_example(
            "Find UserService definition and show me the class",
            """<tool_call>result = goto_definition("src/services/user.py", 45, 20, "UserService")
if result.success:
    loc = result.locations[0]
    content = read_file(loc.file)
    lines = content.split("\\n")
    # Show 10 lines starting from definition
    for i in range(loc.line - 1, min(loc.line + 9, len(lines))):
        print(f"{i+1}: {lines[i]}")
</tool_call>""",
        )
    )

    # Example 2: Check definition range
    examples.append(
        create_example(
            "What's the span of the calculate_total method definition?",
            """<tool_call>result = goto_definition("src/models/order.py", 85, 12, "calculate_total")
if result.success:
    loc = result.locations[0]
    span = loc.end_line - loc.line + 1
    print(f"calculate_total spans {span} lines (lines {loc.line}-{loc.end_line})")
    print(f"Starts at column {loc.column}, ends at column {loc.end_column}")
</tool_call>""",
        )
    )

    # Example 3: Find references and group by directory
    examples.append(
        create_example(
            "Which directories use TypeCheckResult?",
            """<tool_call>result = find_references("src/punie/agent/typed_tools.py", 36, 10, "TypeCheckResult")
if result.success:
    from pathlib import Path
    dirs = set(str(Path(ref.file).parent) for ref in result.references)
    print(f"TypeCheckResult is used in {len(dirs)} directories:")
    for dir_path in sorted(dirs):
        count = sum(1 for ref in result.references if str(Path(ref.file).parent) == dir_path)
        print(f"  {dir_path}: {count} references")
</tool_call>""",
        )
    )

    # Example 4: Check if symbol is in multiple files
    examples.append(
        create_example(
            "Is process defined in multiple files?",
            """<tool_call>result = goto_definition("src/api/main.py", 55, 10, "process")
if result.success:
    files = set(loc.file for loc in result.locations)
    if len(files) > 1:
        print(f"process is defined in {len(files)} different files:")
        for file in sorted(files):
            print(f"  - {file}")
    else:
        print(f"process is defined in only one file: {result.locations[0].file}")
</tool_call>""",
        )
    )

    # Example 5: Find and typecheck definition file
    examples.append(
        create_example(
            "Find UserService and check its file for type errors",
            """<tool_call>result = goto_definition("src/services/user.py", 45, 20, "UserService")
if result.success:
    loc = result.locations[0]
    print(f"UserService defined in {loc.file}")

    # Type check the file
    type_result = typecheck(loc.file)
    if type_result.error_count > 0:
        print(f"Found {type_result.error_count} type errors in definition file")
    else:
        print("No type errors in definition file")
</tool_call>""",
        )
    )

    # Example 6: Reference counting by file type
    examples.append(
        create_example(
            "How many test files vs production files use parse_ty_output?",
            """<tool_call>result = find_references("src/punie/agent/typed_tools.py", 54, 9, "parse_ty_output")
if result.success:
    test_refs = sum(1 for ref in result.references if "test" in ref.file)
    prod_refs = result.reference_count - test_refs
    print(f"parse_ty_output usage:")
    print(f"  Production: {prod_refs} references")
    print(f"  Tests: {test_refs} references")
    print(f"  Total: {result.reference_count}")
</tool_call>""",
        )
    )

    # Example 7: Conditional field access
    examples.append(
        create_example(
            "Find BaseModel definition and check if it's in our code or external",
            """<tool_call>result = goto_definition("src/punie/agent/typed_tools.py", 13, 25, "BaseModel")
if result.success:
    loc = result.locations[0]
    if "site-packages" in loc.file or ".venv" in loc.file:
        print(f"BaseModel is from external library: {loc.file}")
    else:
        print(f"BaseModel is defined in our codebase: {loc.file}:{loc.line}")
</tool_call>""",
        )
    )

    # Example 8: Multi-location handling
    examples.append(
        create_example(
            "Find all definitions of Result and show their locations",
            """<tool_call>result = goto_definition("src/models/base.py", 30, 15, "Result")
if result.success:
    print(f"Found {len(result.locations)} definitions of Result:")
    for i, loc in enumerate(result.locations, 1):
        print(f"{i}. {loc.file}:{loc.line}:{loc.column} (ends at {loc.end_line}:{loc.end_column})")
</tool_call>""",
        )
    )

    # Example 9: Parse error handling
    examples.append(
        create_example(
            "Try to find definition of an unknown symbol",
            """<tool_call>result = goto_definition("src/app.py", 100, 15, "NonExistentSymbol")
if result.parse_error:
    print(f"LSP error: {result.parse_error}")
elif not result.success:
    print("NonExistentSymbol is not defined in the codebase")
else:
    print(f"Found at {result.locations[0].file}:{result.locations[0].line}")
</tool_call>""",
        )
    )

    # Example 10: Reference line numbers
    examples.append(
        create_example(
            "List the exact line numbers where calculate_total is called",
            """<tool_call>result = find_references("src/models/order.py", 85, 12, "calculate_total")
if result.success:
    line_numbers = [ref.line for ref in result.references]
    print(f"calculate_total is called on lines: {', '.join(map(str, sorted(line_numbers)))}")
</tool_call>""",
        )
    )

    # Example 11: Filter references by directory
    examples.append(
        create_example(
            "Show only the API references to UserService",
            """<tool_call>result = find_references("src/services/user.py", 20, 7, "UserService")
if result.success:
    api_refs = [ref for ref in result.references if "api" in ref.file]
    print(f"UserService is used in {len(api_refs)} API files:")
    for ref in api_refs:
        print(f"  {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 12: Compare definition and reference counts
    examples.append(
        create_example(
            "Is process_order defined once but used many times?",
            """<tool_call>def_result = goto_definition("src/api/orders.py", 120, 15, "process_order")
ref_result = find_references("src/api/orders.py", 120, 15, "process_order")

print(f"Definitions: {len(def_result.locations) if def_result.success else 0}")
print(f"References: {ref_result.reference_count if ref_result.success else 0}")

if ref_result.reference_count > len(def_result.locations):
    print("process_order is heavily used throughout the codebase")
</tool_call>""",
        )
    )

    # Example 13: Access all location fields
    examples.append(
        create_example(
            "Show complete location details for TypeCheckResult definition",
            """<tool_call>result = goto_definition("src/punie/agent/typed_tools.py", 36, 10, "TypeCheckResult")
if result.success:
    loc = result.locations[0]
    print(f"Symbol: {result.symbol}")
    print(f"File: {loc.file}")
    print(f"Start: line {loc.line}, column {loc.column}")
    print(f"End: line {loc.end_line}, column {loc.end_column}")
    if loc.preview:
        print(f"Preview: {loc.preview}")
</tool_call>""",
        )
    )

    # Example 14: Iterate and format
    examples.append(
        create_example(
            "Format all parse_ty_output references as clickable links",
            """<tool_call>result = find_references("src/punie/agent/typed_tools.py", 54, 9, "parse_ty_output")
if result.success:
    print(f"Found {result.reference_count} references:")
    for ref in result.references:
        print(f"file://{ref.file}#{ref.line}")
</tool_call>""",
        )
    )

    # Example 15: Success flag with field access
    examples.append(
        create_example(
            "Check if OLD_CONSTANT is still defined, and where",
            """<tool_call>result = goto_definition("src/config.py", 75, 10, "OLD_CONSTANT")
print(f"Success: {result.success}")
print(f"Symbol: {result.symbol}")
if result.success and len(result.locations) > 0:
    loc = result.locations[0]
    print(f"OLD_CONSTANT is defined at {loc.file}:{loc.line}")
else:
    print("OLD_CONSTANT is not defined - safe to remove references")
</tool_call>""",
        )
    )

    return examples


def generate_multi_step_workflows() -> list[dict]:
    """Generate multi-step workflow examples (15)."""
    examples = []

    # Example 1: Find definition, read, and typecheck
    examples.append(
        create_example(
            "Find UserService, read its implementation, and check for type errors",
            """<tool_call># Step 1: Find definition
def_result = goto_definition("src/services/user.py", 45, 20, "UserService")
if not def_result.success:
    print("UserService not found")
else:
    loc = def_result.locations[0]
    print(f"UserService defined at {loc.file}:{loc.line}")

    # Step 2: Read the file
    content = read_file(loc.file)
    print(f"File has {len(content.split(chr(10)))} lines")

    # Step 3: Type check
    type_result = typecheck(loc.file)
    if type_result.error_count > 0:
        print(f"Found {type_result.error_count} type errors:")
        for error in type_result.errors[:3]:
            print(f"  {error.line}: {error.message}")
    else:
        print("No type errors found")
</tool_call>""",
        )
    )

    # Example 2: Find references, group, and check each file
    examples.append(
        create_example(
            "Find all files using TypeCheckResult and check them for type errors",
            """<tool_call>ref_result = find_references("src/punie/agent/typed_tools.py", 36, 10, "TypeCheckResult")
if ref_result.success:
    files = set(ref.file for ref in ref_result.references)
    print(f"Checking {len(files)} files that use TypeCheckResult:")

    for file in sorted(files):
        type_result = typecheck(file)
        status = "✓" if type_result.success else f"✗ ({type_result.error_count} errors)"
        print(f"  {file}: {status}")
</tool_call>""",
        )
    )

    # Example 3: Find definition, find references, analyze usage
    examples.append(
        create_example(
            "Analyze usage patterns of parse_ty_output",
            """<tool_call># Find definition
def_result = goto_definition("src/punie/agent/typed_tools.py", 54, 9, "parse_ty_output")
print(f"parse_ty_output defined at line {def_result.locations[0].line}")

# Find all usages
ref_result = find_references("src/punie/agent/typed_tools.py", 54, 9, "parse_ty_output")
print(f"\\nUsed in {ref_result.reference_count} places:")

# Group by file type
test_refs = [ref for ref in ref_result.references if "test" in ref.file]
prod_refs = [ref for ref in ref_result.references if "test" not in ref.file]

print(f"  Production: {len(prod_refs)} files")
print(f"  Tests: {len(test_refs)} files")
</tool_call>""",
        )
    )

    # Example 4: Navigation + linting
    examples.append(
        create_example(
            "Find UserService definition and lint its file",
            """<tool_call>def_result = goto_definition("src/services/user.py", 45, 20, "UserService")
if def_result.success:
    loc = def_result.locations[0]
    print(f"UserService is in {loc.file}")

    # Lint the file
    lint_result = ruff_check(loc.file)
    if lint_result.success:
        print("No linting violations")
    else:
        print(f"Found {lint_result.violation_count} violations:")
        for v in lint_result.violations[:5]:
            print(f"  {v.line}: {v.code} - {v.message}")
</tool_call>""",
        )
    )

    # Example 5: Find unused definitions
    examples.append(
        create_example(
            "Check if old_helper_function is defined but unused",
            """<tool_call># Check if it exists
def_result = goto_definition("src/utils/helpers.py", 200, 8, "old_helper_function")
if not def_result.success:
    print("old_helper_function is not defined")
else:
    print(f"old_helper_function defined at line {def_result.locations[0].line}")

    # Check if it's used anywhere
    ref_result = find_references("src/utils/helpers.py", 200, 8, "old_helper_function")
    if ref_result.reference_count == 0:
        print("WARNING: Function is defined but never used - consider removing")
    else:
        print(f"Function is used in {ref_result.reference_count} places")
</tool_call>""",
        )
    )

    # Example 6: Compare definitions across versions
    examples.append(
        create_example(
            "Find all definitions of Config and compare their locations",
            """<tool_call>def_result = goto_definition("src/app.py", 15, 10, "Config")
if def_result.success:
    print(f"Found {len(def_result.locations)} definitions of Config:")
    for i, loc in enumerate(def_result.locations, 1):
        print(f"\\n{i}. {loc.file}:{loc.line}")

        # Read context around each definition
        content = read_file(loc.file)
        lines = content.split("\\n")
        start = max(0, loc.line - 2)
        end = min(len(lines), loc.line + 2)
        for j in range(start, end):
            print(f"    {j+1}: {lines[j]}")
</tool_call>""",
        )
    )

    # Example 7: Refactoring helper - find and verify
    examples.append(
        create_example(
            "Before renaming UserService, check where it's used",
            """<tool_call>print("Analyzing UserService before rename...")

# Find definition
def_result = goto_definition("src/services/user.py", 45, 20, "UserService")
print(f"Defined at: {def_result.locations[0].file}:{def_result.locations[0].line}")

# Find all references
ref_result = find_references("src/services/user.py", 45, 20, "UserService")
print(f"\\nFound {ref_result.reference_count} references:")

# Group by file
from pathlib import Path
files_to_update = set(ref.file for ref in ref_result.references)
print(f"\\nWill need to update {len(files_to_update)} files:")
for file in sorted(files_to_update):
    refs_in_file = [ref for ref in ref_result.references if ref.file == file]
    print(f"  {file} ({len(refs_in_file)} occurrences)")
</tool_call>""",
        )
    )

    # Example 8: Impact analysis
    examples.append(
        create_example(
            "What's the impact of changing parse_ruff_output signature?",
            """<tool_call>print("Impact analysis for parse_ruff_output...")

# Find all call sites
ref_result = find_references("src/punie/agent/typed_tools.py", 156, 9, "parse_ruff_output")
print(f"Function is called in {ref_result.reference_count} places")

# Check each file for tests
files_with_tests = []
for ref in ref_result.references:
    if "test" in ref.file:
        files_with_tests.append(ref.file)

print(f"\\nImpact:")
print(f"  {ref_result.reference_count - len(files_with_tests)} production call sites")
print(f"  {len(files_with_tests)} test files to update")

# Check if any have type errors
for file in set(ref.file for ref in ref_result.references):
    type_result = typecheck(file)
    if not type_result.success:
        print(f"  ⚠️  {file} has {type_result.error_count} existing type errors")
</tool_call>""",
        )
    )

    # Example 9: Dependency chain
    examples.append(
        create_example(
            "Find what TypeCheckResult depends on",
            """<tool_call># Find TypeCheckResult definition
def_result = goto_definition("src/punie/agent/typed_tools.py", 36, 10, "TypeCheckResult")
loc = def_result.locations[0]
print(f"TypeCheckResult at {loc.file}:{loc.line}")

# Read its definition
content = read_file(loc.file)
lines = content.split("\\n")
definition = "\\n".join(lines[loc.line-1:loc.end_line])

# Look for dependencies (imports it references)
print("\\nDependencies:")
if "BaseModel" in definition:
    base_result = goto_definition(loc.file, loc.line, 20, "BaseModel")
    if base_result.success:
        print(f"  - BaseModel from {base_result.locations[0].file}")
if "TypeCheckError" in definition:
    print("  - TypeCheckError (defined in same file)")
</tool_call>""",
        )
    )

    # Example 10: Test coverage check
    examples.append(
        create_example(
            "Check test coverage for goto_definition function",
            """<tool_call># Find the function definition
def_result = goto_definition("src/punie/agent/lsp_client.py", 175, 15, "goto_definition")
print(f"goto_definition is defined at line {def_result.locations[0].line}")

# Find all references
ref_result = find_references("src/punie/agent/lsp_client.py", 175, 15, "goto_definition")

# Count test vs production usage
test_refs = [ref for ref in ref_result.references if "test" in ref.file]
prod_refs = [ref for ref in ref_result.references if "test" not in ref.file]

print(f"\\nUsage:")
print(f"  Tests: {len(test_refs)} references")
print(f"  Production: {len(prod_refs)} references")

if len(test_refs) == 0:
    print("⚠️  WARNING: No test coverage!")
elif len(test_refs) < 3:
    print("⚠️  Low test coverage")
else:
    print("✓ Good test coverage")
</tool_call>""",
        )
    )

    # Example 11: Find circular dependencies
    examples.append(
        create_example(
            "Check if UserService has circular dependencies",
            """<tool_call># Find UserService definition
def_result = goto_definition("src/services/user.py", 20, 7, "UserService")
user_file = def_result.locations[0].file

# Find what UserService references
ref_result = find_references(user_file, 20, 7, "UserService")
files_using_user = set(ref.file for ref in ref_result.references)

# Check if any of those files import UserService
print("Checking for circular dependencies...")
circular = []
for file in files_using_user:
    if file != user_file:  # Skip self
        # Check if this file imports from user_file
        content = read_file(file)
        if "from" in content and "user" in content:
            circular.append(file)

if circular:
    print(f"⚠️  Potential circular dependencies in {len(circular)} files:")
    for file in circular:
        print(f"  {file}")
else:
    print("✓ No circular dependencies detected")
</tool_call>""",
        )
    )

    # Example 12: Migration helper
    examples.append(
        create_example(
            "Help migrate from old_api to new_api",
            """<tool_call>print("Migration analysis: old_api → new_api")

# Find all old_api usages
old_refs = find_references("src/api/old.py", 50, 8, "old_api")
print(f"Found {old_refs.reference_count} usages of old_api")

# Check if new_api exists
new_def = goto_definition("src/api/new.py", 30, 8, "new_api")
if new_def.success:
    print("✓ new_api is defined")

    # Group old usages by file
    files_to_migrate = set(ref.file for ref in old_refs.references)
    print(f"\\nFiles to migrate ({len(files_to_migrate)}):")
    for file in sorted(files_to_migrate):
        count = sum(1 for ref in old_refs.references if ref.file == file)
        print(f"  {file}: {count} occurrences")
else:
    print("✗ new_api not found - define it first")
</tool_call>""",
        )
    )

    # Example 13: Code quality workflow
    examples.append(
        create_example(
            "Full quality check for parse_definition_response",
            """<tool_call># Find function definition
def_result = goto_definition("src/punie/agent/typed_tools.py", 417, 9, "parse_definition_response")
loc = def_result.locations[0]
print(f"Analyzing {loc.file}...")

# Run all quality checks
print("\\n1. Type checking:")
type_result = typecheck(loc.file)
print(f"   Errors: {type_result.error_count}")

print("\\n2. Linting:")
lint_result = ruff_check(loc.file)
print(f"   Violations: {lint_result.violation_count}")

print("\\n3. Test coverage:")
ref_result = find_references(loc.file, loc.line, 9, "parse_definition_response")
test_refs = [ref for ref in ref_result.references if "test" in ref.file]
print(f"   Test references: {len(test_refs)}")

# Summary
issues = type_result.error_count + lint_result.violation_count
if issues == 0 and len(test_refs) > 0:
    print("\\n✓ All quality checks passed")
else:
    print(f"\\n⚠️  Found {issues} quality issues")
</tool_call>""",
        )
    )

    # Example 14: Documentation helper
    examples.append(
        create_example(
            "Generate documentation for public API functions",
            """<tool_call># Find all functions in public API
content = read_file("src/api/public.py")
lines = content.split("\\n")

print("Public API functions:")
for i, line in enumerate(lines, 1):
    if line.startswith("def ") and not line.startswith("def _"):
        # Extract function name
        func_name = line.split("(")[0].replace("def ", "")

        # Find references to see usage
        ref_result = find_references("src/api/public.py", i, 5, func_name)

        print(f"\\n{func_name}:")
        print(f"  Defined at line {i}")
        print(f"  Used in {ref_result.reference_count} places")

        # Show first 3 usage examples
        for ref in ref_result.references[:3]:
            print(f"    {ref.file}:{ref.line}")
</tool_call>""",
        )
    )

    # Example 15: Cleanup verification
    examples.append(
        create_example(
            "Verify it's safe to delete deprecated.py",
            """<tool_call>content = read_file("src/deprecated.py")
lines = content.split("\\n")

print("Checking if deprecated.py is safe to delete...")

# Find all function/class definitions
definitions = []
for i, line in enumerate(lines, 1):
    if line.startswith("def ") or line.startswith("class "):
        name = line.split("(")[0].split(":")[0].replace("def ", "").replace("class ", "").strip()
        definitions.append((name, i))

print(f"Found {len(definitions)} definitions")

# Check if any are still referenced
has_references = False
for name, line in definitions:
    ref_result = find_references("src/deprecated.py", line, 5, name)
    external_refs = [ref for ref in ref_result.references if ref.file != "src/deprecated.py"]

    if external_refs:
        has_references = True
        print(f"⚠️  {name} is still used in {len(external_refs)} places:")
        for ref in external_refs[:3]:
            print(f"    {ref.file}:{ref.line}")

if not has_references:
    print("\\n✓ Safe to delete - no external references found")
else:
    print("\\n✗ Cannot delete - still has external references")
</tool_call>""",
        )
    )

    return examples


def generate_direct_answers() -> list[dict]:
    """Generate direct answer examples (10) - no tool calls."""
    examples = []

    # Example 1: What is LSP
    examples.append(
        create_example(
            "What is the Language Server Protocol?",
            """The Language Server Protocol (LSP) is a standardized protocol for communication between code editors/IDEs and language servers that provide language-specific features like:

- Go to definition
- Find references
- Hover information
- Code completion
- Diagnostics (errors/warnings)

LSP separates language intelligence from the editor, allowing any LSP-compliant editor to work with any LSP server. Punie uses ty server's LSP implementation for semantic navigation.""",
        )
    )

    # Example 2: When to use LSP vs text search
    examples.append(
        create_example(
            "When should I use goto_definition instead of grep?",
            """Use goto_definition (LSP) instead of grep when:

1. **Finding symbol definitions** - goto_definition finds the actual definition, not just text matches in comments or strings
2. **Following imports** - jumps through import chains to the original definition
3. **Disambiguating** - handles multiple symbols with the same name correctly
4. **Scope aware** - understands Python scoping rules

Use grep when:
- Searching for arbitrary text patterns
- Finding TODO comments or string literals
- Searching across non-Python files
- Looking for text that isn't a Python symbol""",
        )
    )

    # Example 3: LSP vs AST
    examples.append(
        create_example(
            "What's the difference between LSP and AST parsing?",
            """LSP (Language Server Protocol) and AST (Abstract Syntax Tree) parsing serve different purposes:

**LSP:**
- Semantic analysis across files (cross-file references, imports)
- Real-time type information
- Editor integration features
- Uses language server (ty server for Python)

**AST parsing:**
- Syntactic analysis of single files
- Code transformation and generation
- Static analysis within one file
- Direct Python ast module

Punie uses LSP for navigation (goto_definition, find_references) because it provides semantic understanding across the entire project, not just syntax within one file.""",
        )
    )

    # Example 4: How LSP client works
    examples.append(
        create_example(
            "How does Punie's LSP client work?",
            """Punie's LSP client connects to ty server using the stdio transport:

1. **Initialization** - sends LSP initialize request with client capabilities
2. **Document sync** - sends textDocument/didOpen for files (lazy, on first access)
3. **Requests** - sends textDocument/definition or textDocument/references with file URI and position
4. **Response parsing** - converts LSP responses (0-based positions, file:// URIs) to Pydantic models with 1-based positions

The client is a module-level singleton that persists across tool calls to avoid expensive initialize handshakes. It's implemented in src/punie/agent/lsp_client.py with custom JSON-RPC over stdin/stdout.""",
        )
    )

    # Example 5: Field access importance
    examples.append(
        create_example(
            "Why does the training data emphasize field access?",
            """Field access training is critical based on Phase 23 learnings:

**Problem:** Phase 23 model had 0% field access rate - it would call tools like `result = typecheck("src/")` but never access `result.error_count` or `result.errors`.

**Impact:** Typed tools provided no benefit over raw text - the structured data was ignored.

**Solution:** Phase 26 training data includes explicit field access patterns:
- `if result.success:`
- `for ref in result.references:`
- `print(f"Found {result.reference_count} references")`

**Result:** 22% field access coverage in training → 90% field access in inference (Phase 26.1).

Always show the model accessing structured fields, not just calling tools.""",
        )
    )

    # Example 6: 0-based vs 1-based
    examples.append(
        create_example(
            "Why does LSP use 0-based line numbers?",
            """LSP uses 0-based line and column numbers for historical reasons:

**LSP (0-based):**
- First line: 0
- First column: 0
- Standard in many protocols (JSON-RPC, text editors' internal representations)

**Human-readable (1-based):**
- First line: 1
- First column: 1
- What users see in editors, what Python's error messages use

Punie's LSP client handles conversion automatically:
- Sends 1-based positions to ty server (converted to 0-based)
- Receives 0-based positions from ty server (converted to 1-based)
- Returns 1-based positions in GotoDefinitionResult/FindReferencesResult

Users never see 0-based positions.""",
        )
    )

    # Example 7: When definitions return multiple locations
    examples.append(
        create_example(
            "Why would goto_definition return multiple locations?",
            """goto_definition returns multiple locations when a symbol has multiple definitions:

1. **Method overloading** - different signatures for same method name
2. **Import aliases** - symbol imported in multiple places
3. **Generic type variables** - T defined in multiple generic classes
4. **Namespace collisions** - same name in different modules

Example: `process` might be:
- A function in src/api/process.py
- A method in src/models/Order
- An imported name from external library

The model should check `len(result.locations)` and handle multiple definitions appropriately, usually by showing all locations or filtering by file type.""",
        )
    )

    # Example 8: Performance considerations
    examples.append(
        create_example(
            "Are LSP operations fast enough for production?",
            """Yes, LSP operations are fast enough for production use:

**Measured performance (Phase 26 spike):**
- Initialize: ~100ms (one-time cost)
- goto_definition: 62ms
- find_references: 80ms

**Why it's fast:**
- ty server maintains incremental state (parsed ASTs)
- Persistent connection reuses initialized state
- Native Rust implementation

**Comparison:**
- grep entire codebase: 200-500ms
- AST parse single file: 50-100ms
- LSP goto_definition: 62ms ✓

LSP is faster than grep for finding symbol definitions because it uses cached semantic information rather than scanning all files.""",
        )
    )

    # Example 9: Scope of Phase 26
    examples.append(
        create_example(
            "What LSP features does Phase 26 support?",
            """Phase 26 is a navigation-first slice with only 2 LSP methods:

**Implemented:**
- `goto_definition` - find where a symbol is defined
- `find_references` - find all usages of a symbol

**Not yet implemented (future phases):**
- `hover` - type information at cursor
- `rename` - refactoring operations
- `documentSymbol` - outline/structure view
- `completion` - autocomplete
- `codeAction` - quick fixes
- `diagnostic` - real-time error checking

Phase 26 validates the LSP architecture with low-risk read-only operations before adding more complex features. The infrastructure (LSP client, typed tools pattern) supports all future LSP methods.""",
        )
    )

    # Example 10: Typed tools vs raw text
    examples.append(
        create_example(
            "What's the advantage of typed tools over raw text output?",
            """Typed tools return Pydantic models instead of raw text, enabling:

**Structured access:**
```python
result = goto_definition("src/app.py", 15, 10, "UserService")
print(result.locations[0].file)  # Direct field access
```

vs raw text:
```
"UserService is defined in src/services/user.py:20:7"
```

**Benefits:**
1. **Programmatic access** - no string parsing needed
2. **Type safety** - editor autocomplete, type checking
3. **Composable** - easy to chain operations
4. **Error handling** - `parse_error` field for failures
5. **Field iteration** - `for ref in result.references:`

**Training requirement:** Must show field access patterns explicitly, or model won't use them (Phase 23 lesson: 0% field access without training).""",
        )
    )

    return examples


def main():
    """Generate all LSP navigation training examples."""
    output_dir = Path("data/phase26_lsp_navigation")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate all categories
    examples = []
    examples.extend(generate_simple_goto_definition())
    examples.extend(generate_simple_find_references())
    examples.extend(generate_navigation_with_field_access())
    examples.extend(generate_multi_step_workflows())
    examples.extend(generate_direct_answers())

    # Write to JSONL
    output_file = output_dir / "examples.jsonl"
    with output_file.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"Generated {len(examples)} examples:")
    print(f"  - Simple goto_definition: 15")
    print(f"  - Simple find_references: 15")
    print(f"  - Navigation + field access: 15")
    print(f"  - Multi-step workflows: 15")
    print(f"  - Direct answers: 10")
    print(f"\nOutput: {output_file}")


if __name__ == "__main__":
    main()
