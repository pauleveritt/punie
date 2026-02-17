"""Tests for typed tool parser functions.

Tests parser functions that convert raw tool output to Pydantic models:
- parse_ty_output (TypeCheckResult)
- parse_ruff_output (RuffResult)
- parse_pytest_output (TestResult)
- parse_definition_response (GotoDefinitionResult)
- parse_references_response (FindReferencesResult)
- parse_hover_response (HoverResult)
- parse_document_symbols_response (DocumentSymbolsResult)
- parse_workspace_symbols_response (WorkspaceSymbolsResult)
- parse_git_status_output (GitStatusResult)
- parse_git_diff_output (GitDiffResult)
- parse_git_log_output (GitLogResult)
"""

import json

from punie.agent.typed_tools import (
    parse_definition_response,
    parse_document_symbols_response,
    parse_git_diff_output,
    parse_git_log_output,
    parse_git_status_output,
    parse_hover_response,
    parse_pytest_output,
    parse_references_response,
    parse_ruff_output,
    parse_ty_output,
    parse_workspace_symbols_response,
)


# TypeCheck parsers


def test_parse_ty_output_empty():
    """parse_ty_output handles empty output (no errors)."""
    result = parse_ty_output("")
    assert result.success is True
    assert result.error_count == 0
    assert result.warning_count == 0
    assert len(result.errors) == 0


def test_parse_ty_output_with_errors():
    """parse_ty_output parses ty JSON output with errors."""
    output = json.dumps([
        {
            "file": "test.py",
            "line": 10,
            "column": 5,
            "severity": "error",
            "code": "unresolved-reference",
            "message": "Cannot resolve reference 'foo'",
        }
    ])
    result = parse_ty_output(output)
    assert result.success is False
    assert result.error_count == 1
    assert result.warning_count == 0
    assert len(result.errors) == 1
    assert result.errors[0].file == "test.py"
    assert result.errors[0].line == 10


def test_parse_ty_output_with_warnings():
    """parse_ty_output distinguishes errors from warnings."""
    output = json.dumps([
        {
            "file": "test.py",
            "line": 10,
            "column": 5,
            "severity": "error",
            "code": "unresolved-reference",
            "message": "Cannot resolve reference 'foo'",
        },
        {
            "file": "test.py",
            "line": 15,
            "column": 10,
            "severity": "warning",
            "code": "unused-variable",
            "message": "Variable 'bar' is not used",
        },
    ])
    result = parse_ty_output(output)
    assert result.success is False  # Has errors
    assert result.error_count == 1
    assert result.warning_count == 1
    assert len(result.errors) == 2


def test_parse_ty_output_warnings_only():
    """parse_ty_output with only warnings counts as success."""
    output = json.dumps([
        {
            "file": "test.py",
            "line": 15,
            "column": 10,
            "severity": "warning",
            "code": "unused-variable",
            "message": "Variable 'bar' is not used",
        }
    ])
    result = parse_ty_output(output)
    assert result.success is True  # No errors, only warnings
    assert result.error_count == 0
    assert result.warning_count == 1


def test_parse_ty_output_malformed_json():
    """parse_ty_output handles malformed JSON as failure."""
    result = parse_ty_output("not valid json")
    assert result.success is False  # Parse failure = failure
    assert result.error_count == 0
    assert len(result.errors) == 0
    assert result.parse_error is not None
    assert "failed to parse" in result.parse_error.lower()


def test_parse_ty_output_success_has_no_parse_error():
    """parse_ty_output sets parse_error to None on success."""
    result = parse_ty_output("")
    assert result.parse_error is None


# Ruff parsers


def test_parse_ruff_output_empty():
    """parse_ruff_output handles empty output (no violations)."""
    result = parse_ruff_output("")
    assert result.success is True
    assert result.violation_count == 0
    assert result.fixable_count == 0
    assert len(result.violations) == 0


def test_parse_ruff_output_with_violations():
    """parse_ruff_output parses ruff text output with violations."""
    output = """test.py:10:5: E501 Line too long (89 > 88 characters)
test.py:15:1: F401 [*] `os` imported but unused"""
    result = parse_ruff_output(output)
    assert result.success is False
    assert result.violation_count == 2
    assert result.fixable_count == 1
    assert len(result.violations) == 2
    assert result.violations[0].code == "E501"
    assert result.violations[0].fixable is False
    assert result.violations[1].code == "F401"
    assert result.violations[1].fixable is True


def test_parse_ruff_output_all_fixable():
    """parse_ruff_output counts fixable violations correctly."""
    output = """test.py:10:1: F401 [*] `os` imported but unused
test.py:15:1: F401 [*] `sys` imported but unused"""
    result = parse_ruff_output(output)
    assert result.violation_count == 2
    assert result.fixable_count == 2


def test_parse_ruff_output_ignores_summary_lines():
    """parse_ruff_output ignores summary lines from ruff."""
    output = """test.py:10:5: E501 Line too long
Found 1 error."""
    result = parse_ruff_output(output)
    assert result.violation_count == 1
    assert len(result.violations) == 1


def test_parse_ruff_output_warns_on_unparseable_output():
    """parse_ruff_output sets parse_error when output looks like violations but none parsed."""
    # Output that looks like it should contain violations (has colons and numbers)
    # but doesn't match the expected pattern
    output = "some_file.py:10:5 Something went wrong"
    result = parse_ruff_output(output)
    # This will trigger the parse_error warning
    assert result.parse_error is not None
    assert "format change" in result.parse_error.lower()


def test_parse_ruff_output_no_error_on_valid_empty():
    """parse_ruff_output doesn't set parse_error on legitimately empty output."""
    result = parse_ruff_output("")
    assert result.parse_error is None


# Pytest parsers


def test_parse_pytest_output_empty():
    """parse_pytest_output handles empty output."""
    result = parse_pytest_output("")
    assert result.success is True
    assert result.passed == 0
    assert result.failed == 0
    assert len(result.tests) == 0


def test_parse_pytest_output_all_passed():
    """parse_pytest_output parses successful test run."""
    output = """tests/test_foo.py::test_bar PASSED                       [100%]
tests/test_foo.py::test_baz PASSED                       [100%]
=== 2 passed in 0.05s ==="""
    result = parse_pytest_output(output)
    assert result.success is True
    assert result.passed == 2
    assert result.failed == 0
    assert result.duration == 0.05
    assert len(result.tests) == 2
    assert result.tests[0].name == "tests/test_foo.py::test_bar"
    assert result.tests[0].outcome == "passed"


def test_parse_pytest_output_with_failures():
    """parse_pytest_output parses test failures."""
    output = """tests/test_foo.py::test_bar PASSED                       [50%]
tests/test_foo.py::test_baz FAILED                       [100%]
=== 1 failed, 1 passed in 0.10s ==="""
    result = parse_pytest_output(output)
    assert result.success is False
    assert result.passed == 1
    assert result.failed == 1
    assert result.duration == 0.10
    assert len(result.tests) == 2
    assert result.tests[1].outcome == "failed"


def test_parse_pytest_output_with_errors_and_skipped():
    """parse_pytest_output handles errors and skipped tests."""
    output = """tests/test_foo.py::test_bar PASSED
tests/test_foo.py::test_baz ERROR
tests/test_foo.py::test_qux SKIPPED
=== 1 error, 1 passed, 1 skipped in 0.03s ==="""
    result = parse_pytest_output(output)
    assert result.success is False  # Errors count as failure
    assert result.passed == 1
    assert result.errors == 1
    assert result.skipped == 1
    assert len(result.tests) == 3


def test_parse_pytest_output_warns_on_unparseable_output():
    """parse_pytest_output sets parse_error when output looks like pytest but can't be parsed."""
    # Output that mentions "test" but doesn't match expected format
    output = "Something about tests went wrong but no parseable format"
    result = parse_pytest_output(output)
    assert result.parse_error is not None
    assert "could not be parsed" in result.parse_error.lower()


def test_parse_pytest_output_no_error_on_valid_empty():
    """parse_pytest_output doesn't set parse_error on legitimately empty output."""
    result = parse_pytest_output("")
    assert result.parse_error is None


# LSP Navigation parsers - Goto Definition


def test_parse_definition_response_single_location():
    """parse_definition_response handles single Location."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "uri": "file:///Users/test/project/src/app.py",
            "range": {
                "start": {"line": 9, "character": 6},  # 0-based
                "end": {"line": 9, "character": 15},
            },
        },
    }

    result = parse_definition_response(response, "UserService")

    assert result.success is True
    assert result.symbol == "UserService"
    assert len(result.locations) == 1
    assert result.locations[0].file == "/Users/test/project/src/app.py"
    assert result.locations[0].line == 10  # 1-based
    assert result.locations[0].column == 7  # 1-based
    assert result.locations[0].end_line == 10
    assert result.locations[0].end_column == 16
    assert result.parse_error is None


def test_parse_definition_response_multiple_locations():
    """parse_definition_response handles array of Locations."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "uri": "file:///src/app.py",
                "range": {
                    "start": {"line": 9, "character": 6},
                    "end": {"line": 9, "character": 15},
                },
            },
            {
                "uri": "file:///src/models.py",
                "range": {
                    "start": {"line": 19, "character": 6},
                    "end": {"line": 19, "character": 15},
                },
            },
        ],
    }

    result = parse_definition_response(response, "UserService")

    assert result.success is True
    assert result.symbol == "UserService"
    assert len(result.locations) == 2
    assert result.locations[0].file == "/src/app.py"
    assert result.locations[0].line == 10
    assert result.locations[1].file == "/src/models.py"
    assert result.locations[1].line == 20
    assert result.parse_error is None


def test_parse_definition_response_null_result():
    """parse_definition_response handles null result (not found)."""
    response = {"jsonrpc": "2.0", "id": 1, "result": None}

    result = parse_definition_response(response, "MissingClass")

    assert result.success is False
    assert result.symbol == "MissingClass"
    assert len(result.locations) == 0
    assert result.parse_error is None


def test_parse_definition_response_empty_array():
    """parse_definition_response handles empty array result."""
    response = {"jsonrpc": "2.0", "id": 1, "result": []}

    result = parse_definition_response(response, "MissingClass")

    assert result.success is False
    assert result.symbol == "MissingClass"
    assert len(result.locations) == 0
    assert result.parse_error is None


def test_parse_definition_response_malformed():
    """parse_definition_response sets parse_error on malformed response."""
    response = {"jsonrpc": "2.0", "id": 1, "result": "invalid"}

    result = parse_definition_response(response, "UserService")

    assert result.success is False
    assert result.symbol == "UserService"
    assert len(result.locations) == 0
    assert result.parse_error is not None
    assert "Unexpected result type" in result.parse_error


# LSP Navigation parsers - Find References


def test_parse_references_response_success():
    """parse_references_response handles array of Locations."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "uri": "file:///src/app.py",
                "range": {
                    "start": {"line": 14, "character": 9},  # 0-based
                    "end": {"line": 14, "character": 22},
                },
            },
            {
                "uri": "file:///src/api.py",
                "range": {
                    "start": {"line": 41, "character": 7},
                    "end": {"line": 41, "character": 20},
                },
            },
        ],
    }

    result = parse_references_response(response, "process_order")

    assert result.success is True
    assert result.symbol == "process_order"
    assert result.reference_count == 2
    assert len(result.references) == 2
    assert result.references[0].file == "/src/app.py"
    assert result.references[0].line == 15  # 1-based
    assert result.references[0].column == 10  # 1-based
    assert result.references[1].file == "/src/api.py"
    assert result.references[1].line == 42
    assert result.parse_error is None


def test_parse_references_response_null_result():
    """parse_references_response handles null result (not found)."""
    response = {"jsonrpc": "2.0", "id": 1, "result": None}

    result = parse_references_response(response, "unused_function")

    assert result.success is False
    assert result.symbol == "unused_function"
    assert result.reference_count == 0
    assert len(result.references) == 0
    assert result.parse_error is None


def test_parse_references_response_empty_array():
    """parse_references_response handles empty array result."""
    response = {"jsonrpc": "2.0", "id": 1, "result": []}

    result = parse_references_response(response, "unused_function")

    assert result.success is False
    assert result.symbol == "unused_function"
    assert result.reference_count == 0
    assert len(result.references) == 0
    assert result.parse_error is None


def test_parse_references_response_malformed():
    """parse_references_response sets parse_error on malformed response."""
    response = {"jsonrpc": "2.0", "id": 1, "result": "invalid"}

    result = parse_references_response(response, "process_order")

    assert result.success is False
    assert result.symbol == "process_order"
    assert result.reference_count == 0
    assert len(result.references) == 0
    assert result.parse_error is not None
    assert "Unexpected result type" in result.parse_error


# LSP Navigation parsers - Hover


def test_parse_hover_response_markup_content():
    """parse_hover_response handles MarkupContent format."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "contents": {
                "kind": "markdown",
                "value": "```python\nclass UserService:\n    ...\n```\n\nManages user operations."
            }
        }
    }

    result = parse_hover_response(response, "UserService")

    assert result.success is True
    assert result.symbol == "UserService"
    assert result.content is not None
    assert "class UserService" in result.content
    assert result.language == "markdown"
    assert result.parse_error is None


def test_parse_hover_response_marked_string():
    """parse_hover_response handles MarkedString format."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "contents": {
                "language": "python",
                "value": "def authenticate(user: str, password: str) -> bool"
            }
        }
    }

    result = parse_hover_response(response, "authenticate")

    assert result.success is True
    assert result.symbol == "authenticate"
    assert result.content == "def authenticate(user: str, password: str) -> bool"
    assert result.language == "python"
    assert result.parse_error is None


def test_parse_hover_response_plain_string():
    """parse_hover_response handles plain string format."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "contents": "Simple hover text"
        }
    }

    result = parse_hover_response(response, "some_symbol")

    assert result.success is True
    assert result.symbol == "some_symbol"
    assert result.content == "Simple hover text"
    assert result.language == "plaintext"
    assert result.parse_error is None


def test_parse_hover_response_array_of_strings():
    """parse_hover_response handles array of MarkedStrings."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "contents": [
                "First part",
                {"language": "python", "value": "def foo(): ..."},
                "Third part"
            ]
        }
    }

    result = parse_hover_response(response, "foo")

    assert result.success is True
    assert result.symbol == "foo"
    assert "First part" in result.content
    assert "def foo()" in result.content
    assert "Third part" in result.content
    assert result.parse_error is None


def test_parse_hover_response_null_result():
    """parse_hover_response handles null result (no hover info)."""
    response = {"jsonrpc": "2.0", "id": 1, "result": None}

    result = parse_hover_response(response, "unknown")

    assert result.success is False
    assert result.symbol == "unknown"
    assert result.content is None
    assert result.parse_error is None


def test_parse_hover_response_empty_content():
    """parse_hover_response handles empty content."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "contents": ""
        }
    }

    result = parse_hover_response(response, "symbol")

    assert result.success is False
    assert result.symbol == "symbol"
    assert result.content == ""
    assert result.parse_error is None


# LSP Navigation parsers - Document Symbols


def test_parse_document_symbols_response_hierarchical():
    """parse_document_symbols_response handles hierarchical DocumentSymbol format."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "name": "UserService",
                "kind": 5,  # Class
                "range": {
                    "start": {"line": 10, "character": 0},
                    "end": {"line": 50, "character": 0}
                },
                "children": [
                    {
                        "name": "__init__",
                        "kind": 6,  # Method
                        "range": {
                            "start": {"line": 12, "character": 4},
                            "end": {"line": 15, "character": 0}
                        },
                        "children": []
                    },
                    {
                        "name": "process",
                        "kind": 6,  # Method
                        "range": {
                            "start": {"line": 17, "character": 4},
                            "end": {"line": 25, "character": 0}
                        },
                        "children": []
                    }
                ]
            }
        ]
    }

    result = parse_document_symbols_response(response, "src/services.py")

    assert result.success is True
    assert result.file_path == "src/services.py"
    assert len(result.symbols) == 1
    assert result.symbols[0].name == "UserService"
    assert result.symbols[0].kind == 5
    assert result.symbols[0].line == 11  # 1-based
    assert len(result.symbols[0].children) == 2
    assert result.symbols[0].children[0].name == "__init__"
    assert result.symbol_count == 3  # 1 class + 2 methods
    assert result.parse_error is None


def test_parse_document_symbols_response_flat():
    """parse_document_symbols_response handles flat SymbolInformation format."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "name": "UserService",
                "kind": 5,  # Class
                "location": {
                    "uri": "file:///src/services.py",
                    "range": {
                        "start": {"line": 10, "character": 0},
                        "end": {"line": 50, "character": 0}
                    }
                }
            },
            {
                "name": "process",
                "kind": 6,  # Method
                "location": {
                    "uri": "file:///src/services.py",
                    "range": {
                        "start": {"line": 17, "character": 4},
                        "end": {"line": 25, "character": 0}
                    }
                }
            }
        ]
    }

    result = parse_document_symbols_response(response, "src/services.py")

    assert result.success is True
    assert result.file_path == "src/services.py"
    assert len(result.symbols) == 2
    assert result.symbols[0].name == "UserService"
    assert result.symbols[0].kind == 5
    assert result.symbols[1].name == "process"
    assert result.symbols[1].kind == 6
    assert result.symbol_count == 2
    assert result.parse_error is None


def test_parse_document_symbols_response_null():
    """parse_document_symbols_response handles null result."""
    response = {"jsonrpc": "2.0", "id": 1, "result": None}

    result = parse_document_symbols_response(response, "empty.py")

    assert result.success is False
    assert result.file_path == "empty.py"
    assert len(result.symbols) == 0
    assert result.symbol_count == 0
    assert result.parse_error is None


def test_parse_document_symbols_response_empty_array():
    """parse_document_symbols_response handles empty array."""
    response = {"jsonrpc": "2.0", "id": 1, "result": []}

    result = parse_document_symbols_response(response, "empty.py")

    assert result.success is False
    assert result.file_path == "empty.py"
    assert len(result.symbols) == 0
    assert result.symbol_count == 0
    assert result.parse_error is None


# LSP Navigation parsers - Workspace Symbols


def test_parse_workspace_symbols_response_success():
    """parse_workspace_symbols_response handles successful search."""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "name": "ApiClient",
                "kind": 5,  # Class
                "location": {
                    "uri": "file:///src/api/client.py",
                    "range": {
                        "start": {"line": 15, "character": 6},
                        "end": {"line": 100, "character": 0}
                    }
                },
                "containerName": "api.client"
            },
            {
                "name": "ApiClient",
                "kind": 5,
                "location": {
                    "uri": "file:///src/api/v2/client.py",
                    "range": {
                        "start": {"line": 20, "character": 6},
                        "end": {"line": 80, "character": 0}
                    }
                },
                "containerName": "api.v2.client"
            }
        ]
    }

    result = parse_workspace_symbols_response(response, "ApiClient")

    assert result.success is True
    assert result.query == "ApiClient"
    assert result.symbol_count == 2
    assert len(result.symbols) == 2
    assert result.symbols[0].name == "ApiClient"
    assert result.symbols[0].kind == 5
    assert result.symbols[0].file == "/src/api/client.py"
    assert result.symbols[0].line == 16  # 1-based
    assert result.symbols[0].container_name == "api.client"
    assert result.symbols[1].container_name == "api.v2.client"
    assert result.parse_error is None


def test_parse_workspace_symbols_response_null():
    """parse_workspace_symbols_response handles null result."""
    response = {"jsonrpc": "2.0", "id": 1, "result": None}

    result = parse_workspace_symbols_response(response, "NonExistent")

    assert result.success is False
    assert result.query == "NonExistent"
    assert result.symbol_count == 0
    assert len(result.symbols) == 0
    assert result.parse_error is None


def test_parse_workspace_symbols_response_empty():
    """parse_workspace_symbols_response handles empty array."""
    response = {"jsonrpc": "2.0", "id": 1, "result": []}

    result = parse_workspace_symbols_response(response, "nothing")

    assert result.success is False
    assert result.query == "nothing"
    assert result.symbol_count == 0
    assert len(result.symbols) == 0
    assert result.parse_error is None


# Git parsers - Git Status


def test_parse_git_status_output_clean():
    """parse_git_status_output handles clean working tree."""
    result = parse_git_status_output("")

    assert result.success is True
    assert result.clean is True
    assert result.file_count == 0
    assert len(result.files) == 0
    assert result.parse_error is None


def test_parse_git_status_output_mixed_changes():
    """parse_git_status_output handles mixed staged and unstaged changes."""
    output = """M  src/app.py
 M src/config.py
A  src/new.py
?? src/untracked.py
R  old.py -> renamed.py"""

    result = parse_git_status_output(output)

    assert result.success is True
    assert result.clean is False
    assert result.file_count == 5
    assert len(result.files) == 5

    # Staged modified
    assert result.files[0].file == "src/app.py"
    assert result.files[0].status == "modified"
    assert result.files[0].staged is True

    # Unstaged modified
    assert result.files[1].file == "src/config.py"
    assert result.files[1].status == "modified"
    assert result.files[1].staged is False

    # Staged added
    assert result.files[2].file == "src/new.py"
    assert result.files[2].status == "added"
    assert result.files[2].staged is True

    # Untracked
    assert result.files[3].file == "src/untracked.py"
    assert result.files[3].status == "untracked"
    assert result.files[3].staged is False

    # Renamed (uses new name)
    assert result.files[4].file == "renamed.py"
    assert result.files[4].status == "renamed"
    assert result.files[4].staged is True

    assert result.parse_error is None


# Git parsers - Git Diff


def test_parse_git_diff_output_empty():
    """parse_git_diff_output handles no changes."""
    result = parse_git_diff_output("")

    assert result.success is True
    assert result.file_count == 0
    assert result.additions == 0
    assert result.deletions == 0
    assert len(result.files) == 0
    assert result.parse_error is None


def test_parse_git_diff_output_single_file():
    """parse_git_diff_output handles single file diff."""
    output = """diff --git a/src/app.py b/src/app.py
index abc1234..def5678 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,7 +10,8 @@ def process():
     return result

 def new_function():
-    old_line
+    new_line
+    another_line
     return value"""

    result = parse_git_diff_output(output)

    assert result.success is True
    assert result.file_count == 1
    assert len(result.files) == 1
    assert result.files[0].file == "src/app.py"
    assert result.files[0].additions == 2
    assert result.files[0].deletions == 1
    assert result.additions == 2
    assert result.deletions == 1
    assert len(result.files[0].hunks) == 1
    assert result.parse_error is None


def test_parse_git_diff_output_multiple_files():
    """parse_git_diff_output handles multiple file diffs."""
    output = """diff --git a/src/app.py b/src/app.py
index abc1234..def5678 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,3 +10,4 @@ def process():
+    new_line
diff --git a/src/config.py b/src/config.py
index 111222..333444 100644
--- a/src/config.py
+++ b/src/config.py
@@ -5,2 +5,1 @@ DEBUG = True
-    removed_line
-    another_removed"""

    result = parse_git_diff_output(output)

    assert result.success is True
    assert result.file_count == 2
    assert result.additions == 1
    assert result.deletions == 2
    assert result.files[0].file == "src/app.py"
    assert result.files[0].additions == 1
    assert result.files[0].deletions == 0
    assert result.files[1].file == "src/config.py"
    assert result.files[1].additions == 0
    assert result.files[1].deletions == 2
    assert result.parse_error is None


# Git parsers - Git Log


def test_parse_git_log_output_empty():
    """parse_git_log_output handles no commits."""
    result = parse_git_log_output("")

    assert result.success is True
    assert result.commit_count == 0
    assert len(result.commits) == 0
    assert result.parse_error is None


def test_parse_git_log_output_oneline():
    """parse_git_log_output handles formatted output with author and date."""
    output = """abc1234|John Doe|Mon Feb 16 10:30:00 2026 -0500|feat: add new feature
def5678|Jane Smith|Mon Feb 16 09:15:00 2026 -0500|fix: resolve bug in auth
789abcd|Bob Wilson|Sun Feb 15 18:45:00 2026 -0500|docs: update README"""

    result = parse_git_log_output(output)

    assert result.success is True
    assert result.commit_count == 3
    assert len(result.commits) == 3
    assert result.commits[0].hash == "abc1234"
    assert result.commits[0].author == "John Doe"
    assert result.commits[0].date == "Mon Feb 16 10:30:00 2026 -0500"
    assert result.commits[0].message == "feat: add new feature"
    assert result.commits[1].hash == "def5678"
    assert result.commits[1].author == "Jane Smith"
    assert result.commits[1].message == "fix: resolve bug in auth"
    assert result.commits[2].hash == "789abcd"
    assert result.commits[2].message == "docs: update README"
    assert result.parse_error is None
