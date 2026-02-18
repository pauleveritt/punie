"""Tests for CST core parse utilities."""

from pathlib import Path

import pytest

libcst = pytest.importorskip("libcst")

from punie.cst.core import parse_file, parse_source  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "cst"


def test_parse_source_simple():
    """parse_source should return a Module for simple code."""
    module = parse_source("x = 1\n")
    assert module is not None
    assert module.code == "x = 1\n"


def test_parse_source_function():
    """parse_source should handle function definitions."""
    code = "def foo():\n    return 42\n"
    module = parse_source(code)
    assert module.code == code


def test_parse_source_empty():
    """parse_source should handle empty strings."""
    module = parse_source("")
    assert module is not None
    assert module.code == ""


def test_parse_source_invalid_syntax():
    """parse_source should raise for invalid syntax."""
    with pytest.raises(Exception):
        parse_source("def foo(:\n")


def test_parse_file_simple_module():
    """parse_file should parse the simple_module.py fixture."""
    module = parse_file(str(FIXTURES / "simple_module.py"))
    assert module is not None
    assert "greet" in module.code


def test_parse_file_preserves_content():
    """parse_file should preserve all source content (round-trip)."""
    fixture_path = str(FIXTURES / "simple_module.py")
    with open(fixture_path) as f:
        original = f.read()
    module = parse_file(fixture_path)
    assert module.code == original


def test_parse_file_not_found():
    """parse_file should raise FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        parse_file("/nonexistent/path/file.py")


def test_parse_file_invalid_component():
    """parse_file should parse the invalid_component fixture (valid Python)."""
    module = parse_file(str(FIXTURES / "invalid_component.py"))
    assert module is not None
    assert "BadGreeting" in module.code
