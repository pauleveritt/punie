"""Typed tools with structured output for domain-specific operations.

This module provides Pydantic models for tools that return structured data
instead of raw text. Currently supports:
- ty (type checking) → TypeCheckResult
- ruff (linting) → RuffResult
- pytest (testing) → TestResult
- LSP navigation (goto_definition, find_references) → GotoDefinitionResult, FindReferencesResult
"""

import json
import re

from pydantic import BaseModel


class TypeCheckError(BaseModel):
    """A single type checking error from ty.

    Attributes:
        file: File path where the error occurred
        line: Line number (1-indexed)
        column: Column number (1-indexed)
        severity: Error severity level ("error" or "warning")
        code: Error code (e.g., "unresolved-reference", "type-mismatch")
        message: Human-readable error message
    """

    file: str
    line: int
    column: int
    severity: str  # "error" | "warning"
    code: str
    message: str


class TypeCheckResult(BaseModel):
    """Result of running ty type checker.

    Attributes:
        success: True if no errors found, False otherwise
        error_count: Number of errors found
        warning_count: Number of warnings found
        errors: List of errors and warnings
        parse_error: Error message if output parsing failed, None otherwise
    """

    success: bool
    error_count: int
    warning_count: int
    errors: list[TypeCheckError]
    parse_error: str | None = None


def parse_ty_output(output: str) -> TypeCheckResult:
    """Parse ty check output into TypeCheckResult.

    Args:
        output: Raw output from ty check command (JSON format)

    Returns:
        TypeCheckResult with parsed errors

    Note:
        Expects ty to be run with --output-format json flag.
        If output is empty or malformed, returns success=True with no errors.
    """
    # Handle empty output (no errors)
    if not output or output.strip() == "":
        return TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[])

    try:
        # Parse JSON output from ty
        data = json.loads(output)

        # ty --output-format json returns a list of diagnostics
        # Each diagnostic has: file, line, column, severity, code, message
        errors = []
        error_count = 0
        warning_count = 0

        for diag in data:
            error = TypeCheckError(
                file=diag["file"],
                line=diag["line"],
                column=diag.get("column", 0),
                severity=diag.get("severity", "error"),
                code=diag.get("code", "unknown"),
                message=diag["message"],
            )
            errors.append(error)

            if error.severity == "error":
                error_count += 1
            elif error.severity == "warning":
                warning_count += 1

        success = error_count == 0
        return TypeCheckResult(
            success=success,
            error_count=error_count,
            warning_count=warning_count,
            errors=errors,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # If parsing fails, return failure with parse error
        return TypeCheckResult(
            success=False,
            error_count=0,
            warning_count=0,
            errors=[],
            parse_error=f"Failed to parse ty output: {e}",
        )


# Ruff models


class RuffViolation(BaseModel):
    """A single linting violation from ruff.

    Attributes:
        file: File path where the violation occurred
        line: Line number (1-indexed)
        column: Column number (1-indexed)
        code: Ruff rule code (e.g., "E501", "F401")
        message: Human-readable description of the violation
        fixable: Whether ruff can auto-fix this violation
    """

    file: str
    line: int
    column: int
    code: str
    message: str
    fixable: bool


class RuffResult(BaseModel):
    """Result of running ruff check.

    Attributes:
        success: True if no violations found, False otherwise
        violation_count: Total number of violations found
        fixable_count: Number of violations that can be auto-fixed
        violations: List of all violations
        parse_error: Error message if output parsing failed, None otherwise
    """

    success: bool
    violation_count: int
    fixable_count: int
    violations: list[RuffViolation]
    parse_error: str | None = None


def parse_ruff_output(output: str) -> RuffResult:
    """Parse ruff check output into RuffResult.

    Args:
        output: Raw output from ruff check command (text format)

    Returns:
        RuffResult with parsed violations

    Note:
        Parses default ruff text output format:
        path/to/file.py:10:5: E501 Line too long (89 > 88 characters)
        path/to/file.py:15:1: F401 [*] `os` imported but unused

        [*] indicates fixable violations
    """
    # Handle empty output (no violations)
    if not output or output.strip() == "":
        return RuffResult(
            success=True, violation_count=0, fixable_count=0, violations=[]
        )

    violations = []
    fixable_count = 0

    # Pattern: file.py:line:col: CODE message
    # [*] prefix indicates fixable
    pattern = r"^(.+?):(\d+):(\d+):\s+([A-Z]\d+)\s+(\[\*\]\s+)?(.+)$"

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("Found ") or line.startswith("No "):
            continue

        match = re.match(pattern, line)
        if match:
            file_path, line_no, col_no, code, fixable_marker, message = match.groups()
            is_fixable = fixable_marker is not None

            violation = RuffViolation(
                file=file_path,
                line=int(line_no),
                column=int(col_no),
                code=code,
                message=message.strip(),
                fixable=is_fixable,
            )
            violations.append(violation)

            if is_fixable:
                fixable_count += 1

    success = len(violations) == 0
    parse_error = None

    # If we have non-empty output but found no violations, warn about possible format change
    if output.strip() and not violations:
        # Check if output looks like actual violations (has colons and line numbers)
        if ":" in output and any(char.isdigit() for char in output):
            parse_error = "Non-empty output with no violations parsed - possible format change"

    return RuffResult(
        success=success,
        violation_count=len(violations),
        fixable_count=fixable_count,
        violations=violations,
        parse_error=parse_error,
    )


# Pytest models


class TestCase(BaseModel):
    """A single test case result from pytest.

    Attributes:
        name: Test identifier (e.g., "tests/test_foo.py::test_bar")
        outcome: Test outcome ("passed", "failed", "error", "skipped")
        duration: Test execution time in seconds
        message: Error/failure message if test didn't pass (optional)
    """

    name: str
    outcome: str  # "passed" | "failed" | "error" | "skipped"
    duration: float
    message: str | None = None


class TestResult(BaseModel):
    """Result of running pytest.

    Attributes:
        success: True if all tests passed, False otherwise
        passed: Number of tests that passed
        failed: Number of tests that failed
        errors: Number of tests with errors
        skipped: Number of tests that were skipped
        duration: Total test execution time in seconds
        tests: List of individual test results
        parse_error: Error message if output parsing failed, None otherwise
    """

    success: bool
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float
    tests: list[TestCase]
    parse_error: str | None = None


def parse_pytest_output(output: str) -> TestResult:
    """Parse pytest output into TestResult.

    Args:
        output: Raw output from pytest -v --tb=short command

    Returns:
        TestResult with parsed test results

    Note:
        Parses pytest verbose output format:
        tests/test_foo.py::test_bar PASSED                       [100%]
        tests/test_foo.py::test_baz FAILED                       [100%]

        Summary line: === 1 failed, 1 passed in 0.05s ===
    """
    # Handle empty output
    if not output or output.strip() == "":
        return TestResult(
            success=True,
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            duration=0.0,
            tests=[],
        )

    tests = []
    passed = failed = errors = skipped = 0
    duration = 0.0

    lines = output.strip().split("\n")

    # Parse individual test results
    test_pattern = r"^(.+?)\s+(PASSED|FAILED|ERROR|SKIPPED)"
    for line in lines:
        match = re.match(test_pattern, line)
        if match:
            test_name, outcome = match.groups()
            test_name = test_name.strip()
            outcome = outcome.lower()

            # Try to extract duration from verbose output (not always present)
            duration_match = re.search(r"\[(\d+\.\d+)s\]", line)
            test_duration = float(duration_match.group(1)) if duration_match else 0.0

            test_case = TestCase(
                name=test_name,
                outcome=outcome,
                duration=test_duration,
                message=None,  # Would need --tb output parsing for messages
            )
            tests.append(test_case)

            # Count outcomes
            if outcome == "passed":
                passed += 1
            elif outcome == "failed":
                failed += 1
            elif outcome == "error":
                errors += 1
            elif outcome == "skipped":
                skipped += 1

    # Parse summary line: === 1 failed, 2 passed in 0.05s ===
    summary_pattern = r"===.*?(?:(\d+)\s+failed)?.*?(?:(\d+)\s+passed)?.*?(?:(\d+)\s+error)?.*?(?:(\d+)\s+skipped)?.*?in\s+([\d.]+)s"
    for line in lines:
        match = re.search(summary_pattern, line)
        if match:
            f, p, e, s, dur = match.groups()
            if f:
                failed = int(f)
            if p:
                passed = int(p)
            if e:
                errors = int(e)
            if s:
                skipped = int(s)
            duration = float(dur)
            break

    success = failed == 0 and errors == 0
    parse_error = None

    # If we have non-empty output but found no tests or summary, warn about parsing failure
    if output.strip() and not tests and duration == 0.0:
        # Check if output looks like pytest output (contains test-related keywords)
        if any(keyword in output.lower() for keyword in ["test", "passed", "failed", "error"]):
            parse_error = "Non-empty pytest output could not be parsed - possible format change"

    return TestResult(
        success=success,
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        duration=duration,
        tests=tests,
        parse_error=parse_error,
    )


# LSP Navigation models


class DefinitionLocation(BaseModel):
    """A single definition location from LSP goto_definition.

    Attributes:
        file: Absolute file path
        line: Line number (1-based)
        column: Column number (1-based)
        end_line: End line number (1-based)
        end_column: End column number (1-based)
        preview: Short preview of the code at this location (optional)
    """

    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    preview: str | None = None


class GotoDefinitionResult(BaseModel):
    """Result of LSP goto_definition operation.

    Attributes:
        success: True if definition(s) found, False otherwise
        symbol: Symbol name being searched
        locations: List of definition locations (may be empty if not found)
        parse_error: Error message if LSP response parsing failed, None otherwise
    """

    success: bool
    symbol: str
    locations: list[DefinitionLocation]
    parse_error: str | None = None


def parse_definition_response(response: dict, symbol: str) -> GotoDefinitionResult:
    """Parse LSP textDocument/definition response into GotoDefinitionResult.

    Args:
        response: LSP response dict with 'result' field (Location | Location[] | null)
        symbol: Symbol name being searched (for error messages)

    Returns:
        GotoDefinitionResult with locations (or parse_error if parsing fails)

    Note:
        Handles both single Location and array of Locations.
        Converts LSP 0-based line/column to 1-based for human readability.
        Returns success=False if result is null or empty array.
    """
    try:
        result = response.get("result")

        # Handle null result (symbol not found)
        if result is None:
            return GotoDefinitionResult(
                success=False,
                symbol=symbol,
                locations=[],
                parse_error=None,
            )

        # Normalize to array (LSP allows single Location or array)
        if isinstance(result, dict):
            locations_raw = [result]
        elif isinstance(result, list):
            locations_raw = result
        else:
            return GotoDefinitionResult(
                success=False,
                symbol=symbol,
                locations=[],
                parse_error=f"Unexpected result type: {type(result)}",
            )

        # Parse each location
        locations = []
        for loc in locations_raw:
            # Extract file path from URI (file:///path → /path)
            uri = loc.get("uri", "")
            if uri.startswith("file://"):
                file_path = uri[7:]  # Remove file://
            else:
                file_path = uri

            # Extract range (0-based → 1-based)
            range_data = loc.get("range", {})
            start = range_data.get("start", {})
            end = range_data.get("end", {})

            location = DefinitionLocation(
                file=file_path,
                line=start.get("line", 0) + 1,  # 0-based → 1-based
                column=start.get("character", 0) + 1,
                end_line=end.get("line", 0) + 1,
                end_column=end.get("character", 0) + 1,
                preview=None,  # Could be populated by reading file
            )
            locations.append(location)

        success = len(locations) > 0
        return GotoDefinitionResult(
            success=success,
            symbol=symbol,
            locations=locations,
            parse_error=None,
        )

    except (KeyError, TypeError, ValueError) as e:
        return GotoDefinitionResult(
            success=False,
            symbol=symbol,
            locations=[],
            parse_error=f"Failed to parse LSP definition response: {e}",
        )


class ReferenceLocation(BaseModel):
    """A single reference location from LSP find_references.

    Attributes:
        file: Absolute file path
        line: Line number (1-based)
        column: Column number (1-based)
        preview: Short preview of the code at this location (optional)
    """

    file: str
    line: int
    column: int
    preview: str | None = None


class FindReferencesResult(BaseModel):
    """Result of LSP find_references operation.

    Attributes:
        success: True if reference(s) found, False otherwise
        symbol: Symbol name being searched
        reference_count: Total number of references found
        references: List of reference locations (may be empty if not found)
        parse_error: Error message if LSP response parsing failed, None otherwise
    """

    success: bool
    symbol: str
    reference_count: int
    references: list[ReferenceLocation]
    parse_error: str | None = None


def parse_references_response(response: dict, symbol: str) -> FindReferencesResult:
    """Parse LSP textDocument/references response into FindReferencesResult.

    Args:
        response: LSP response dict with 'result' field (Location[] | null)
        symbol: Symbol name being searched (for error messages)

    Returns:
        FindReferencesResult with references (or parse_error if parsing fails)

    Note:
        Converts LSP 0-based line/column to 1-based for human readability.
        Returns success=False if result is null or empty array.
    """
    try:
        result = response.get("result")

        # Handle null result (no references found)
        if result is None:
            return FindReferencesResult(
                success=False,
                symbol=symbol,
                reference_count=0,
                references=[],
                parse_error=None,
            )

        # Result should be an array of Locations
        if not isinstance(result, list):
            return FindReferencesResult(
                success=False,
                symbol=symbol,
                reference_count=0,
                references=[],
                parse_error=f"Unexpected result type: {type(result)}",
            )

        # Parse each reference
        references = []
        for loc in result:
            # Extract file path from URI (file:///path → /path)
            uri = loc.get("uri", "")
            if uri.startswith("file://"):
                file_path = uri[7:]  # Remove file://
            else:
                file_path = uri

            # Extract position (0-based → 1-based)
            range_data = loc.get("range", {})
            start = range_data.get("start", {})

            reference = ReferenceLocation(
                file=file_path,
                line=start.get("line", 0) + 1,  # 0-based → 1-based
                column=start.get("character", 0) + 1,
                preview=None,  # Could be populated by reading file
            )
            references.append(reference)

        success = len(references) > 0
        return FindReferencesResult(
            success=success,
            symbol=symbol,
            reference_count=len(references),
            references=references,
            parse_error=None,
        )

    except (KeyError, TypeError, ValueError) as e:
        return FindReferencesResult(
            success=False,
            symbol=symbol,
            reference_count=0,
            references=[],
            parse_error=f"Failed to parse LSP references response: {e}",
        )


# Hover models


class HoverResult(BaseModel):
    """Result of LSP hover operation.

    Attributes:
        success: True if hover info found, False otherwise
        symbol: Symbol name being searched
        content: Hover content (markdown or plaintext)
        language: Language identifier for content (e.g., "python", "markdown")
        parse_error: Error message if LSP response parsing failed, None otherwise
    """

    success: bool
    symbol: str
    content: str | None = None
    language: str | None = None
    parse_error: str | None = None


def parse_hover_response(response: dict, symbol: str) -> HoverResult:
    """Parse LSP textDocument/hover response into HoverResult.

    Args:
        response: LSP response dict with 'result' field (Hover | null)
        symbol: Symbol name being searched (for error messages)

    Returns:
        HoverResult with content (or parse_error if parsing fails)

    Note:
        Handles both MarkupContent and MarkedString formats.
        Returns success=False if result is null.
    """
    try:
        result = response.get("result")

        # Handle null result (no hover info)
        if result is None:
            return HoverResult(
                success=False,
                symbol=symbol,
                content=None,
                parse_error=None,
            )

        # Extract contents (can be MarkupContent | MarkedString | MarkedString[])
        contents = result.get("contents")
        if contents is None:
            return HoverResult(
                success=False,
                symbol=symbol,
                content=None,
                parse_error="No contents in hover response",
            )

        # Parse different content formats
        content_text = None
        language = None

        if isinstance(contents, dict):
            # MarkupContent: {kind: "markdown", value: "..."}
            # MarkedString: {language: "python", value: "..."}
            if "kind" in contents:
                content_text = contents.get("value", "")
                language = contents.get("kind", "plaintext")
            elif "language" in contents:
                content_text = contents.get("value", "")
                language = contents.get("language", "python")
        elif isinstance(contents, str):
            # Simple string
            content_text = contents
            language = "plaintext"
        elif isinstance(contents, list):
            # Array of MarkedString - join them
            parts = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            content_text = "\n\n".join(parts)
            language = "plaintext"

        success = content_text is not None and len(content_text) > 0
        return HoverResult(
            success=success,
            symbol=symbol,
            content=content_text,
            language=language,
            parse_error=None,
        )

    except (KeyError, TypeError, ValueError) as e:
        return HoverResult(
            success=False,
            symbol=symbol,
            content=None,
            parse_error=f"Failed to parse LSP hover response: {e}",
        )


# Document Symbols models


class SymbolInfo(BaseModel):
    """A single symbol from LSP document symbols.

    Attributes:
        name: Symbol name
        kind: Symbol kind (e.g., 1=File, 2=Module, 5=Class, 6=Method, 12=Function)
        line: Start line number (1-based)
        end_line: End line number (1-based)
        children: Nested child symbols (for classes/modules)
    """

    name: str
    kind: int
    line: int
    end_line: int
    children: list["SymbolInfo"] = []


class DocumentSymbolsResult(BaseModel):
    """Result of LSP document symbols operation.

    Attributes:
        success: True if symbols found, False otherwise
        file_path: File path being queried
        symbols: List of top-level symbols in the document
        symbol_count: Total number of symbols (including nested)
        parse_error: Error message if LSP response parsing failed, None otherwise
    """

    success: bool
    file_path: str
    symbols: list[SymbolInfo]
    symbol_count: int = 0
    parse_error: str | None = None


def _count_symbols(symbols: list[SymbolInfo]) -> int:
    """Recursively count symbols including children."""
    count = len(symbols)
    for symbol in symbols:
        count += _count_symbols(symbol.children)
    return count


def _parse_document_symbol(symbol: dict) -> SymbolInfo:
    """Parse a single DocumentSymbol recursively."""
    range_data = symbol.get("range", {})
    start = range_data.get("start", {})
    end = range_data.get("end", {})

    children = []
    if "children" in symbol and symbol["children"]:
        children = [_parse_document_symbol(child) for child in symbol["children"]]

    return SymbolInfo(
        name=symbol.get("name", "unknown"),
        kind=symbol.get("kind", 0),
        line=start.get("line", 0) + 1,  # 0-based → 1-based
        end_line=end.get("line", 0) + 1,
        children=children,
    )


def parse_document_symbols_response(
    response: dict, file_path: str
) -> DocumentSymbolsResult:
    """Parse LSP textDocument/documentSymbol response into DocumentSymbolsResult.

    Args:
        response: LSP response dict with 'result' field (DocumentSymbol[] | SymbolInformation[] | null)
        file_path: File path being queried (for error messages)

    Returns:
        DocumentSymbolsResult with symbols (or parse_error if parsing fails)

    Note:
        Handles both DocumentSymbol[] (hierarchical) and SymbolInformation[] (flat).
        Returns success=False if result is null or empty.
    """
    try:
        result = response.get("result")

        # Handle null result (no symbols)
        if result is None:
            return DocumentSymbolsResult(
                success=False,
                file_path=file_path,
                symbols=[],
                symbol_count=0,
                parse_error=None,
            )

        # Result should be an array
        if not isinstance(result, list):
            return DocumentSymbolsResult(
                success=False,
                file_path=file_path,
                symbols=[],
                symbol_count=0,
                parse_error=f"Unexpected result type: {type(result)}",
            )

        # Parse symbols
        symbols = []
        for item in result:
            # DocumentSymbol has "range" and "selectionRange"
            # SymbolInformation has "location"
            if "range" in item:
                # DocumentSymbol (hierarchical)
                symbols.append(_parse_document_symbol(item))
            elif "location" in item:
                # SymbolInformation (flat) - convert to SymbolInfo
                location = item.get("location", {})
                range_data = location.get("range", {})
                start = range_data.get("start", {})
                end = range_data.get("end", {})

                symbols.append(
                    SymbolInfo(
                        name=item.get("name", "unknown"),
                        kind=item.get("kind", 0),
                        line=start.get("line", 0) + 1,
                        end_line=end.get("line", 0) + 1,
                        children=[],
                    )
                )

        symbol_count = _count_symbols(symbols)
        success = len(symbols) > 0
        return DocumentSymbolsResult(
            success=success,
            file_path=file_path,
            symbols=symbols,
            symbol_count=symbol_count,
            parse_error=None,
        )

    except (KeyError, TypeError, ValueError) as e:
        return DocumentSymbolsResult(
            success=False,
            file_path=file_path,
            symbols=[],
            symbol_count=0,
            parse_error=f"Failed to parse LSP document symbols response: {e}",
        )


# Workspace Symbols models


class WorkspaceSymbol(BaseModel):
    """A single symbol from LSP workspace symbols.

    Attributes:
        name: Symbol name
        kind: Symbol kind (e.g., 5=Class, 6=Method, 12=Function)
        file: File path where symbol is defined
        line: Line number (1-based)
        container_name: Container name (e.g., class name for methods)
    """

    name: str
    kind: int
    file: str
    line: int
    container_name: str | None = None


class WorkspaceSymbolsResult(BaseModel):
    """Result of LSP workspace symbols operation.

    Attributes:
        success: True if symbols found, False otherwise
        query: Search query string
        symbols: List of matching workspace symbols
        symbol_count: Total number of symbols found
        parse_error: Error message if LSP response parsing failed, None otherwise
    """

    success: bool
    query: str
    symbols: list[WorkspaceSymbol]
    symbol_count: int = 0
    parse_error: str | None = None


def parse_workspace_symbols_response(response: dict, query: str) -> WorkspaceSymbolsResult:
    """Parse LSP workspace/symbol response into WorkspaceSymbolsResult.

    Args:
        response: LSP response dict with 'result' field (SymbolInformation[] | WorkspaceSymbol[] | null)
        query: Search query string (for error messages)

    Returns:
        WorkspaceSymbolsResult with symbols (or parse_error if parsing fails)

    Note:
        Converts LSP 0-based line numbers to 1-based for human readability.
        Returns success=False if result is null or empty array.
    """
    try:
        result = response.get("result")

        # Handle null result (no symbols found)
        if result is None:
            return WorkspaceSymbolsResult(
                success=False,
                query=query,
                symbols=[],
                symbol_count=0,
                parse_error=None,
            )

        # Result should be an array
        if not isinstance(result, list):
            return WorkspaceSymbolsResult(
                success=False,
                query=query,
                symbols=[],
                symbol_count=0,
                parse_error=f"Unexpected result type: {type(result)}",
            )

        # Parse each symbol
        symbols = []
        for item in result:
            # Extract location
            location = item.get("location", {})
            uri = location.get("uri", "")

            # Convert file:// URI to path
            if uri.startswith("file://"):
                file_path = uri[7:]
            else:
                file_path = uri

            # Extract position (0-based → 1-based)
            range_data = location.get("range", {})
            start = range_data.get("start", {})

            symbol = WorkspaceSymbol(
                name=item.get("name", "unknown"),
                kind=item.get("kind", 0),
                file=file_path,
                line=start.get("line", 0) + 1,
                container_name=item.get("containerName"),
            )
            symbols.append(symbol)

        success = len(symbols) > 0
        return WorkspaceSymbolsResult(
            success=success,
            query=query,
            symbols=symbols,
            symbol_count=len(symbols),
            parse_error=None,
        )

    except (KeyError, TypeError, ValueError) as e:
        return WorkspaceSymbolsResult(
            success=False,
            query=query,
            symbols=[],
            symbol_count=0,
            parse_error=f"Failed to parse LSP workspace symbols response: {e}",
        )


# Git models


class GitFileStatus(BaseModel):
    """A single file status from git status.

    Attributes:
        file: File path
        status: Status code ("modified", "added", "deleted", "untracked", "renamed", "copied")
        staged: True if changes are staged, False otherwise
    """

    file: str
    status: str
    staged: bool


class GitStatusResult(BaseModel):
    """Result of git status operation.

    Attributes:
        success: True if command executed successfully, False otherwise
        clean: True if working tree is clean (no changes), False otherwise
        file_count: Total number of files with changes
        files: List of file statuses
        parse_error: Error message if output parsing failed, None otherwise
    """

    success: bool
    clean: bool
    file_count: int
    files: list[GitFileStatus]
    parse_error: str | None = None


def parse_git_status_output(output: str) -> GitStatusResult:
    """Parse git status --porcelain output into GitStatusResult.

    Args:
        output: Raw output from git status --porcelain command

    Returns:
        GitStatusResult with file statuses

    Note:
        Parses porcelain format:
        M  modified_staged.py
         M modified_unstaged.py
        A  added_staged.py
        ?? untracked.py
        R  old.py -> new.py
    """
    # Handle empty output (clean working tree)
    if not output or output.strip() == "":
        return GitStatusResult(
            success=True,
            clean=True,
            file_count=0,
            files=[],
        )

    files = []

    for line in output.strip().split("\n"):
        if len(line) < 3:
            continue

        # Porcelain format: XY filename (X=staged, Y=unstaged)
        x, y = line[0], line[1]
        filename = line[3:].strip()

        # Handle renames (format: "R  old -> new")
        if " -> " in filename:
            filename = filename.split(" -> ")[1]  # Use new name

        # Determine status and staging
        if x == "?" and y == "?":
            status = "untracked"
            staged = False
        elif x == "A":
            status = "added"
            staged = True
        elif x == "M":
            status = "modified"
            staged = True
        elif x == "D":
            status = "deleted"
            staged = True
        elif x == "R":
            status = "renamed"
            staged = True
        elif x == "C":
            status = "copied"
            staged = True
        elif y == "M":
            status = "modified"
            staged = False
        elif y == "D":
            status = "deleted"
            staged = False
        else:
            status = "unknown"
            staged = x != " "

        files.append(GitFileStatus(file=filename, status=status, staged=staged))

    clean = len(files) == 0
    return GitStatusResult(
        success=True,
        clean=clean,
        file_count=len(files),
        files=files,
        parse_error=None,
    )


class DiffFile(BaseModel):
    """A single file diff from git diff.

    Attributes:
        file: File path
        additions: Number of lines added
        deletions: Number of lines deleted
        hunks: List of diff hunk strings (optional, for detailed view)
    """

    file: str
    additions: int
    deletions: int
    hunks: list[str] = []


class GitDiffResult(BaseModel):
    """Result of git diff operation.

    Attributes:
        success: True if command executed successfully, False otherwise
        file_count: Number of files changed
        additions: Total lines added across all files
        deletions: Total lines deleted across all files
        files: List of file diffs
        parse_error: Error message if output parsing failed, None otherwise
    """

    success: bool
    file_count: int
    additions: int
    deletions: int
    files: list[DiffFile]
    parse_error: str | None = None


def parse_git_diff_output(output: str) -> GitDiffResult:
    """Parse git diff output into GitDiffResult.

    Args:
        output: Raw output from git diff [--staged] command

    Returns:
        GitDiffResult with file changes

    Note:
        Parses standard diff format with +++ /--- lines for files.
        Counts additions (+) and deletions (-) in hunks.
    """
    # Handle empty output (no changes)
    if not output or output.strip() == "":
        return GitDiffResult(
            success=True,
            file_count=0,
            additions=0,
            deletions=0,
            files=[],
        )

    files = []
    current_file = None
    current_additions = 0
    current_deletions = 0
    current_hunks = []

    for line in output.split("\n"):
        # New file marker
        if line.startswith("+++"):
            # Save previous file
            if current_file:
                files.append(
                    DiffFile(
                        file=current_file,
                        additions=current_additions,
                        deletions=current_deletions,
                        hunks=current_hunks,
                    )
                )

            # Start new file (strip +++ b/ prefix)
            filename = line[4:].strip()
            if filename.startswith("b/"):
                filename = filename[2:]
            current_file = filename
            current_additions = 0
            current_deletions = 0
            current_hunks = []

        # Hunk marker (save it)
        elif line.startswith("@@"):
            current_hunks.append(line)

        # Addition line
        elif line.startswith("+") and not line.startswith("+++"):
            current_additions += 1

        # Deletion line
        elif line.startswith("-") and not line.startswith("---"):
            current_deletions += 1

    # Save last file
    if current_file:
        files.append(
            DiffFile(
                file=current_file,
                additions=current_additions,
                deletions=current_deletions,
                hunks=current_hunks,
            )
        )

    total_additions = sum(f.additions for f in files)
    total_deletions = sum(f.deletions for f in files)

    return GitDiffResult(
        success=True,
        file_count=len(files),
        additions=total_additions,
        deletions=total_deletions,
        files=files,
        parse_error=None,
    )


class GitCommit(BaseModel):
    """A single commit from git log.

    Attributes:
        hash: Commit hash (short or full)
        message: Commit message
        author: Commit author name
        date: Commit date string
    """

    hash: str
    message: str
    author: str | None = None
    date: str | None = None


class GitLogResult(BaseModel):
    """Result of git log operation.

    Attributes:
        success: True if command executed successfully, False otherwise
        commits: List of commits
        commit_count: Total number of commits returned
        parse_error: Error message if output parsing failed, None otherwise
    """

    success: bool
    commits: list[GitCommit]
    commit_count: int
    parse_error: str | None = None


def parse_git_log_output(output: str) -> GitLogResult:
    """Parse git log --format output into GitLogResult.

    Args:
        output: Raw output from git log --format='%h|%an|%ad|%s' -n COUNT command

    Returns:
        GitLogResult with commits

    Note:
        Parses formatted output with author and date:
        abc1234|John Doe|Mon Feb 16 10:30:00 2026 -0500|Commit message here
        def5678|Jane Smith|Mon Feb 16 09:15:00 2026 -0500|Another commit
    """
    # Handle empty output (no commits)
    if not output or output.strip() == "":
        return GitLogResult(
            success=True,
            commits=[],
            commit_count=0,
        )

    commits = []

    for line in output.strip().split("\n"):
        if not line:
            continue

        # Format: "hash|author|date|message"
        parts = line.split("|", maxsplit=3)
        if len(parts) < 4:
            # Fallback for malformed lines
            continue

        commit_hash, author, date, message = parts[0], parts[1], parts[2], parts[3]
        commits.append(GitCommit(hash=commit_hash, author=author, date=date, message=message))

    return GitLogResult(
        success=True,
        commits=commits,
        commit_count=len(commits),
        parse_error=None,
    )
