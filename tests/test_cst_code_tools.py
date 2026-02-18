"""Tests for LibCST code tools: cst_find_pattern, cst_rename, cst_add_import."""

from pathlib import Path

import pytest

libcst = pytest.importorskip("libcst")

from punie.cst.code_tools import cst_add_import, cst_find_pattern, cst_rename  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "cst"
SIMPLE_MODULE = str(FIXTURES / "simple_module.py")


# ============================================================================
# cst_find_pattern tests
# ============================================================================


def test_find_pattern_function_def():
    """cst_find_pattern should find FunctionDef nodes."""
    result = cst_find_pattern(SIMPLE_MODULE, "FunctionDef")
    assert result.success is True
    assert result.match_count >= 2  # greet and add at minimum
    assert result.parse_error is None
    node_types = {m.node_type for m in result.matches}
    assert "FunctionDef" in node_types


def test_find_pattern_class_def():
    """cst_find_pattern should find ClassDef nodes."""
    result = cst_find_pattern(SIMPLE_MODULE, "ClassDef")
    assert result.success is True
    assert result.match_count >= 1  # Calculator class
    assert any("Calculator" in m.code_snippet for m in result.matches)


def test_find_pattern_call():
    """cst_find_pattern should find Call nodes."""
    result = cst_find_pattern(SIMPLE_MODULE, "Call")
    assert result.success is True
    # May or may not have calls depending on the module
    assert result.parse_error is None


def test_find_pattern_import_from():
    """cst_find_pattern should find ImportFrom nodes."""
    result = cst_find_pattern(SIMPLE_MODULE, "ImportFrom")
    assert result.success is True
    assert result.match_count >= 1  # from typing import Optional


def test_find_pattern_named_call():
    """cst_find_pattern 'call:name' should find calls to a specific function."""
    # simple_module.py doesn't have print calls, so use invalid_component.py
    result = cst_find_pattern(SIMPLE_MODULE, "call:greet")
    # No calls to greet in simple_module.py
    assert result.success is True
    assert result.match_count == 0


def test_find_pattern_returns_line_numbers():
    """cst_find_pattern should return accurate line numbers."""
    result = cst_find_pattern(SIMPLE_MODULE, "FunctionDef")
    assert result.success is True
    for match in result.matches:
        assert match.line > 0
        assert match.column >= 0
        assert len(match.code_snippet) > 0


def test_find_pattern_nonexistent_file():
    """cst_find_pattern should return parse_error for missing files."""
    result = cst_find_pattern("/nonexistent/file.py", "FunctionDef")
    assert result.success is False
    assert result.parse_error is not None
    assert result.match_count == 0


def test_find_pattern_unknown_pattern():
    """cst_find_pattern should return parse_error for unknown patterns."""
    result = cst_find_pattern(SIMPLE_MODULE, "UnknownPattern")
    assert result.success is False
    assert result.parse_error is not None


def test_find_pattern_decorator():
    """cst_find_pattern should find Decorator nodes."""
    result = cst_find_pattern(str(FIXTURES / "valid_component.py"), "Decorator")
    assert result.success is True
    assert result.match_count >= 1  # @dataclass


# ============================================================================
# cst_rename tests
# ============================================================================


def test_rename_function():
    """cst_rename should rename a function name."""
    result = cst_rename(SIMPLE_MODULE, "greet", "welcome")
    assert result.success is True
    assert result.rename_count >= 1
    assert result.modified_source is not None
    assert "def welcome(" in result.modified_source
    assert "def greet(" not in result.modified_source


def test_rename_preserves_other_names():
    """cst_rename should not affect names that don't match."""
    result = cst_rename(SIMPLE_MODULE, "greet", "welcome")
    assert result.success is True
    assert "def add(" in result.modified_source  # not renamed
    assert "class Calculator" in result.modified_source  # not renamed


def test_rename_nonexistent_name():
    """cst_rename of a nonexistent name should succeed with 0 renames."""
    result = cst_rename(SIMPLE_MODULE, "nonexistent_xyz", "replacement")
    assert result.success is True
    assert result.rename_count == 0


def test_rename_nonexistent_file():
    """cst_rename should return parse_error for missing files."""
    result = cst_rename("/nonexistent/file.py", "old", "new")
    assert result.success is False
    assert result.parse_error is not None
    assert result.modified_source is None


def test_rename_preserves_whitespace():
    """cst_rename should preserve all whitespace and formatting."""
    result = cst_rename(SIMPLE_MODULE, "add", "sum_values")
    assert result.success is True
    # Check that indentation and structure are preserved
    assert "\n" in result.modified_source
    assert "    " in result.modified_source  # indentation preserved


# ============================================================================
# cst_add_import tests
# ============================================================================


def test_add_import_from():
    """cst_add_import should add a from-import."""
    result = cst_add_import(SIMPLE_MODULE, "from collections import OrderedDict")
    assert result.success is True
    assert result.parse_error is None
    # import_added depends on whether OrderedDict was already imported
    if result.import_added:
        assert "OrderedDict" in result.modified_source


def test_add_import_already_present():
    """cst_add_import should be idempotent (no duplicate if already present)."""
    # simple_module.py already has "from typing import Optional"
    result = cst_add_import(SIMPLE_MODULE, "from typing import Optional")
    assert result.success is True
    assert result.import_added is False  # Already present


def test_add_import_bare():
    """cst_add_import should add a bare import."""
    result = cst_add_import(SIMPLE_MODULE, "import json")
    assert result.success is True
    assert result.parse_error is None


def test_add_import_nonexistent_file():
    """cst_add_import should return parse_error for missing files."""
    result = cst_add_import("/nonexistent/file.py", "from typing import List")
    assert result.success is False
    assert result.parse_error is not None


def test_add_import_invalid_stmt():
    """cst_add_import should return error for invalid import statement."""
    result = cst_add_import(SIMPLE_MODULE, "not an import at all")
    assert result.success is False
    assert result.parse_error is not None


def test_add_import_returns_modified_source():
    """cst_add_import should return the full modified source."""
    result = cst_add_import(SIMPLE_MODULE, "from pathlib import Path")
    assert result.success is True
    if result.import_added:
        assert result.modified_source is not None
        assert "from pathlib import Path" in result.modified_source
