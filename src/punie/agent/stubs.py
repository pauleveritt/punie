"""Generate Python function stubs from toolset for model code generation.

The model needs to know what external functions are available when generating Python
code. This module extracts function signatures from toolset.py and generates clean
stubs (without RunContext parameters) that can be injected into the system prompt.
"""

import inspect
from typing import Callable

from punie.agent import toolset


def _strip_ctx_parameter(sig: inspect.Signature) -> inspect.Signature:
    """Remove the ctx: RunContext[ACPDeps] parameter from signature.

    Args:
        sig: Original function signature

    Returns:
        Signature with ctx parameter removed
    """
    return sig.replace(
        parameters=[p for p in sig.parameters.values() if p.name != "ctx"]
    )


def _format_parameter(param: inspect.Parameter) -> str:
    """Format a parameter with its type annotation.

    Args:
        param: Parameter to format

    Returns:
        String like "path: str" or "args: list[str] | None = None"
    """
    result = param.name

    if param.annotation != inspect.Parameter.empty:
        # Convert annotation to string, handle generics
        annotation = param.annotation
        if hasattr(annotation, "__origin__"):
            # Generic type like list[str]
            result += f": {str(annotation).replace('typing.', '')}"
        else:
            # Simple type like str
            result += f": {annotation.__name__ if hasattr(annotation, '__name__') else str(annotation)}"

    if param.default != inspect.Parameter.empty:
        result += f" = {param.default!r}"

    return result


def _generate_stub(func: Callable, name: str) -> str:
    """Generate a stub string for a single function.

    Args:
        func: Function to generate stub for
        name: Function name

    Returns:
        Stub string like:
        def read_file(path: str) -> str:
            \"\"\"Read contents of a text file from the IDE workspace.\"\"\"
            ...
    """
    sig = inspect.signature(func)
    sig_stripped = _strip_ctx_parameter(sig)

    # Format parameters
    params = [_format_parameter(p) for p in sig_stripped.parameters.values()]
    params_str = ", ".join(params)

    # Format return type
    return_annotation = ""
    if sig.return_annotation != inspect.Signature.empty:
        return_annotation = f" -> {sig.return_annotation.__name__ if hasattr(sig.return_annotation, '__name__') else str(sig.return_annotation)}"

    # Extract first line of docstring
    doc = inspect.getdoc(func) or "External function."
    first_line = doc.split("\n")[0]

    return f"""def {name}({params_str}){return_annotation}:
    \"\"\"{first_line}\"\"\"
    ..."""


def generate_stubs() -> str:
    """Generate Python stubs for all core toolset functions.

    Returns:
        String containing all function stubs that can be injected into system prompt

    Example:
        >>> stubs = generate_stubs()
        >>> "def read_file(path: str) -> str:" in stubs
        True
        >>> "RunContext" in stubs
        False
    """
    core_functions = [
        ("read_file", toolset.read_file),
        ("write_file", toolset.write_file),
        ("run_command", toolset.run_command),
    ]

    stubs = []
    stubs.append("# External functions available in sandbox\n")

    for name, func in core_functions:
        stubs.append(_generate_stub(func, name))
        stubs.append("")  # Blank line between functions

    # Add typed tool stubs manually (not in toolset, but available in sandbox)
    stubs.append("""def typecheck(path: str) -> TypeCheckResult:
    \"\"\"Run ty type checker on a file or directory and return structured results.

    Returns TypeCheckResult with:
    - success: True if no errors found
    - error_count: Number of errors
    - warning_count: Number of warnings
    - errors: List of TypeCheckError objects with file, line, column, severity, code, message

    Example:
        result = typecheck("src/")
        if not result.success:
            for error in result.errors:
                print(f"{error.file}:{error.line} - {error.message}")
    \"\"\"
    ...""")

    stubs.append("""def ruff_check(path: str) -> RuffResult:
    \"\"\"Run ruff linter on a file or directory and return structured results.

    Returns RuffResult with:
    - success: True if no violations found
    - violation_count: Total number of violations
    - fixable_count: Number of auto-fixable violations
    - violations: List of RuffViolation objects with file, line, column, code, message, fixable

    Example:
        result = ruff_check("src/")
        if not result.success:
            fixable = [v for v in result.violations if v.fixable]
            print(f"Found {len(fixable)} fixable violations")
    \"\"\"
    ...""")

    stubs.append("""def pytest_run(path: str) -> TestResult:
    \"\"\"Run pytest on a file or directory and return structured results.

    Returns TestResult with:
    - success: True if all tests passed
    - passed: Number of tests that passed
    - failed: Number of tests that failed
    - errors: Number of tests with errors
    - skipped: Number of skipped tests
    - duration: Total test execution time in seconds
    - tests: List of TestCase objects with name, outcome, duration, message

    Example:
        result = pytest_run("tests/")
        if not result.success:
            for test in result.tests:
                if test.outcome == "failed":
                    print(f"{test.name} failed: {test.message}")
    \"\"\"
    ...""")

    stubs.append("""def goto_definition(file_path: str, line: int, column: int, symbol: str) -> GotoDefinitionResult:
    \"\"\"Find the definition location of a symbol using LSP.

    Returns GotoDefinitionResult with:
    - success: True if definition found
    - symbol: Symbol name being searched
    - locations: List of DefinitionLocation objects with file, line, column, end_line, end_column, preview
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = goto_definition("src/app.py", 15, 10, "UserService")
        if result.success:
            loc = result.locations[0]
            print(f"Defined at {loc.file}:{loc.line}:{loc.column}")
            content = read_file(loc.file)  # Can read the definition file
    \"\"\"
    ...""")

    stubs.append("""def find_references(file_path: str, line: int, column: int, symbol: str) -> FindReferencesResult:
    \"\"\"Find all references to a symbol using LSP.

    Returns FindReferencesResult with:
    - success: True if references found
    - symbol: Symbol name being searched
    - reference_count: Total number of references found
    - references: List of ReferenceLocation objects with file, line, column, preview
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = find_references("src/services/user.py", 20, 7, "UserService")
        if result.success:
            print(f"Found {result.reference_count} references")
            for ref in result.references:
                print(f"  {ref.file}:{ref.line}")
    \"\"\"
    ...""")

    stubs.append("""def hover(file_path: str, line: int, column: int, symbol: str) -> HoverResult:
    \"\"\"Get hover information (type info, docstring) for a symbol using LSP.

    Returns HoverResult with:
    - success: True if hover info found
    - symbol: Symbol name being searched
    - content: Hover content (markdown or plaintext)
    - language: Language identifier (e.g., "python", "markdown")
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = hover("src/app.py", 15, 10, "UserService")
        if result.success:
            print(f"Type info: {result.content}")
    \"\"\"
    ...""")

    stubs.append("""def document_symbols(file_path: str) -> DocumentSymbolsResult:
    \"\"\"Get all symbols (classes, functions, variables) in a file using LSP.

    Returns DocumentSymbolsResult with:
    - success: True if symbols found
    - file_path: File path being queried
    - symbols: List of SymbolInfo objects with name, kind, line, end_line, children
    - symbol_count: Total number of symbols (including nested)
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = document_symbols("src/services/user.py")
        if result.success:
            print(f"Found {result.symbol_count} symbols")
            for symbol in result.symbols:
                print(f"  {symbol.name} (kind={symbol.kind}) at line {symbol.line}")
    \"\"\"
    ...""")

    stubs.append("""def workspace_symbols(query: str) -> WorkspaceSymbolsResult:
    \"\"\"Search for symbols across the entire workspace using LSP.

    Returns WorkspaceSymbolsResult with:
    - success: True if symbols found
    - query: Search query string
    - symbols: List of WorkspaceSymbol objects with name, kind, file, line, container_name
    - symbol_count: Total number of symbols found
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = workspace_symbols("UserService")
        if result.success:
            print(f"Found {result.symbol_count} matches")
            for match in result.symbols:
                print(f"  {match.name} in {match.file}:{match.line}")
    \"\"\"
    ...""")

    stubs.append("""def git_status(path: str) -> GitStatusResult:
    \"\"\"Get git working tree status with structured file information.

    Returns GitStatusResult with:
    - success: True if command executed successfully
    - clean: True if working tree is clean (no changes)
    - file_count: Total number of files with changes
    - files: List of GitFileStatus objects with file, status, staged
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = git_status(".")
        if not result.clean:
            staged = [f for f in result.files if f.staged]
            print(f"Found {len(staged)} staged files")
    \"\"\"
    ...""")

    stubs.append("""def git_diff(path: str, staged: bool = False) -> GitDiffResult:
    \"\"\"Get git diff with structured change information.

    Returns GitDiffResult with:
    - success: True if command executed successfully
    - file_count: Number of files changed
    - additions: Total lines added across all files
    - deletions: Total lines deleted across all files
    - files: List of DiffFile objects with file, additions, deletions, hunks
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = git_diff(".", staged=True)
        if result.file_count > 0:
            print(f"Staged changes: +{result.additions} -{result.deletions}")
            for file in result.files:
                print(f"  {file.file}: +{file.additions} -{file.deletions}")
    \"\"\"
    ...""")

    stubs.append("""def git_log(path: str, count: int = 10) -> GitLogResult:
    \"\"\"Get git commit history with structured commit information.

    Returns GitLogResult with:
    - success: True if command executed successfully
    - commits: List of GitCommit objects with hash, author, date, message
    - commit_count: Total number of commits returned
    - parse_error: Error message if operation failed, None otherwise

    Example:
        result = git_log(".", count=5)
        if result.commit_count > 0:
            print(f"Recent {result.commit_count} commits:")
            for commit in result.commits:
                print(f"  {commit.hash} by {commit.author} on {commit.date}")
                print(f"    {commit.message}")
    \"\"\"
    ...""")

    return "\n".join(stubs)


def get_stub_instructions() -> str:
    """Get instructions for the model on how to use code mode.

    Returns:
        System prompt addition explaining code mode
    """
    return """
## Code Mode — Multi-Step Tool Execution

You can execute multiple tool calls in a single turn by generating Python code.
Use the `execute_code` tool with Python that calls the available external functions.

Available external functions:
```python
{stubs}
```

Constraints:
- No classes allowed (functions only)
- Limited stdlib (no os, pathlib, subprocess, sys)
- Use only the external functions provided above
- Print results to show output to the user
- Handle errors with try/except

Example multi-step query:
User: "Find all Python files and count imports"

Use the execute_code tool with this code:
```python
# Find all Python files
files_output = run_command("find", args=["-name", "*.py"])
files = files_output.strip().split("\\n")

# Count imports in each file
total_imports = 0
for file_path in files:
    content = read_file(file_path)
    total_imports += content.count("import ")

print(f"Found {{total_imports}} imports across {{len(files)}} Python files")
```
""".format(
        stubs=generate_stubs()
    )
