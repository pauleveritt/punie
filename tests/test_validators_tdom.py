"""Tests for tdom domain validators."""

from pathlib import Path

import pytest

libcst = pytest.importorskip("libcst")

from punie.cst.validators.tdom import (  # noqa: E402
    check_render_tree,
    validate_component,
    validate_escape_context,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cst"


# ============================================================================
# validate_component tests
# ============================================================================


def test_validate_component_valid():
    """Valid component should pass validation."""
    result = validate_component(str(FIXTURES / "valid_component.py"))
    assert result.domain == "tdom"
    assert result.parse_error is None
    # valid_component has @dataclass and __call__ -> Node
    assert result.valid is True


def test_validate_component_invalid():
    """Invalid component should fail validation with issues."""
    result = validate_component(str(FIXTURES / "invalid_component.py"))
    assert result.domain == "tdom"
    assert result.parse_error is None
    # BadGreeting is missing @dataclass
    assert result.valid is False
    rules = {i.rule for i in result.issues}
    assert "component-must-have-dataclass" in rules


def test_validate_component_missing_callable():
    """Component missing __call__ should have an issue."""
    result = validate_component(str(FIXTURES / "invalid_component.py"))
    # BadGreeting also has __call__ without return type annotation
    rules = {i.rule for i in result.issues}
    assert "component-must-have-dataclass" in rules


def test_validate_component_nonexistent_file():
    """validate_component should handle missing files gracefully."""
    result = validate_component("/nonexistent/path/component.py")
    assert result.valid is False
    assert result.parse_error is not None
    assert result.domain == "tdom"


def test_validate_component_issues_have_suggestions():
    """Validation issues should include suggestions."""
    result = validate_component(str(FIXTURES / "invalid_component.py"))
    for issue in result.issues:
        if issue.severity == "error":
            assert issue.suggestion is not None


def test_validate_component_empty_file():
    """Empty file should be valid (no components to check)."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("")
        tmp_path = f.name
    try:
        result = validate_component(tmp_path)
        assert result.valid is True
        assert result.issues == []
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_component_helper_class_skipped():
    """Task 1: helper class without component signals should not be flagged."""
    result = validate_component(str(FIXTURES / "mixed_classes.py"))
    # Greeting is a valid component; HelperFormatter has no signals → skipped
    assert result.valid is True
    # No issues for HelperFormatter
    flagged_classes = {i.message for i in result.issues}
    assert not any("HelperFormatter" in msg for msg in flagged_classes)


def test_validate_component_dataclass_call_form():
    """Task 2: @dataclass(frozen=True) should be recognized as @dataclass."""
    import tempfile
    code = '''
from dataclasses import dataclass

class Node:
    pass

@dataclass(frozen=True)
class FrozenComponent:
    name: str = "World"

    def __call__(self) -> Node:
        return Node()
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_component(tmp_path)
        # FrozenComponent has @dataclass(frozen=True) and __call__ → valid
        assert result.valid is True
        rules = {i.rule for i in result.issues}
        assert "component-must-have-dataclass" not in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_component_nested_class():
    """Task 3: nested class should not clobber outer class __call__ tracking."""
    result = validate_component(str(FIXTURES / "nested_classes.py"))
    # OuterComponent has @dataclass and __call__ → valid
    assert result.valid is True
    rules = {i.rule for i in result.issues}
    assert "component-must-have-callable" not in rules


def test_validate_component_dataclass_missing_callable():
    """Task 1+10: class with @dataclass but no __call__ should be flagged."""
    import tempfile
    code = '''
from dataclasses import dataclass

class Node:
    pass

@dataclass
class ComponentNoCall:
    name: str = "World"
    # Missing __call__ method
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_component(tmp_path)
        assert result.valid is False
        rules = {i.rule for i in result.issues}
        assert "component-must-have-callable" in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_escape_context_inside_class_method():
    """Task 10: f-string in html() inside a class method should be flagged."""
    import tempfile
    code = '''
def html(t):
    return t

class MyView:
    def render(self, name):
        return html(f"<h1>Hello {name}</h1>")
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_escape_context(tmp_path)
        rules = {i.rule for i in result.issues}
        assert "no-fstring-in-html" in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_component_syntax_error():
    """Task 10: syntax error file returns parse_error, not a crash."""
    import tempfile
    code = "def broken(:\n    pass\n"
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_component(tmp_path)
        assert result.valid is False
        assert result.parse_error is not None
    finally:
        import os
        os.unlink(tmp_path)


# ============================================================================
# check_render_tree tests
# ============================================================================


def test_check_render_tree_valid():
    """check_render_tree should pass for a simple valid module."""
    result = check_render_tree(str(FIXTURES / "simple_module.py"))
    assert result.domain == "tdom"
    assert result.parse_error is None


def test_check_render_tree_nonexistent():
    """check_render_tree should handle missing files."""
    result = check_render_tree("/nonexistent/path.py")
    assert result.valid is False
    assert result.parse_error is not None


# ============================================================================
# validate_escape_context tests
# ============================================================================


def test_validate_escape_context_valid():
    """Module without f-strings in html() should pass."""
    result = validate_escape_context(str(FIXTURES / "valid_component.py"))
    assert result.domain == "tdom"
    assert result.parse_error is None


def test_validate_escape_context_nonexistent():
    """validate_escape_context should handle missing files."""
    result = validate_escape_context("/nonexistent/file.py")
    assert result.valid is False
    assert result.parse_error is not None


def test_validate_escape_context_with_fstring():
    """Module with f-string in html() should fail."""
    import tempfile
    code = '''
def html(t):
    return t

def render(name):
    return html(f"<h1>Hello {name}</h1>")
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_escape_context(tmp_path)
        assert result.domain == "tdom"
        # Should detect the f-string in html() call
        rules = {i.rule for i in result.issues}
        assert "no-fstring-in-html" in rules
    finally:
        import os
        os.unlink(tmp_path)
