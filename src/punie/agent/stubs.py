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

    # Add typecheck stub manually (not in toolset, but available in sandbox)
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

Response:
<tool_call><function=execute_code><parameter=code>
# Find all Python files
files_output = run_command("find", args=["-name", "*.py"])
files = files_output.strip().split("\\n")

# Count imports in each file
total_imports = 0
for file_path in files:
    content = read_file(file_path)
    total_imports += content.count("import ")

print(f"Found {{total_imports}} imports across {{len(files)}} Python files")
</parameter></function></tool_call>
""".format(
        stubs=generate_stubs()
    )
