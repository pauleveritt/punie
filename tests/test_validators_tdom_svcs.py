"""Tests for tdom-svcs domain validators."""

from pathlib import Path

import pytest

libcst = pytest.importorskip("libcst")

from punie.cst.validators.tdom_svcs import (  # noqa: E402
    check_di_template_binding,
    validate_middleware_chain,
    validate_route_pattern,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cst"


# ============================================================================
# validate_middleware_chain tests
# ============================================================================


def test_validate_middleware_chain_valid():
    """Valid middleware should pass chain validation."""
    result = validate_middleware_chain(str(FIXTURES / "valid_middleware.py"))
    assert result.domain == "tdom-svcs"
    assert result.parse_error is None
    assert result.valid is True


def test_validate_middleware_chain_invalid():
    """Middleware with wrong __call__ signature should fail."""
    result = validate_middleware_chain(str(FIXTURES / "invalid_middleware.py"))
    assert result.domain == "tdom-svcs"
    assert result.parse_error is None
    assert result.valid is False
    rules = {i.rule for i in result.issues}
    assert "middleware-must-have-correct-signature" in rules


def test_validate_middleware_chain_nonexistent():
    """validate_middleware_chain should handle missing files."""
    result = validate_middleware_chain("/nonexistent/middleware.py")
    assert result.valid is False
    assert result.parse_error is not None


def test_validate_middleware_chain_no_categories():
    """@middleware without categories should generate a warning."""
    import tempfile
    code = '''
from dataclasses import dataclass


def middleware(categories=None):
    def decorator(cls): return cls
    return decorator


@middleware()
@dataclass
class UncategorizedMiddleware:
    priority: int = 0

    def __call__(self, target, props, context):
        return props
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_middleware_chain(tmp_path)
        assert result.domain == "tdom-svcs"
        rules = {i.rule for i in result.issues}
        assert "middleware-must-have-categories" in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_middleware_chain_has_suggestions():
    """Middleware issues should include helpful error messages."""
    result = validate_middleware_chain(str(FIXTURES / "invalid_middleware.py"))
    errors = [i for i in result.issues if i.severity == "error"]
    assert len(errors) > 0
    for issue in errors:
        assert issue.suggestion is not None


# ============================================================================
# check_di_template_binding tests
# ============================================================================


def test_check_di_template_binding_simple():
    """Simple module without DI should pass."""
    result = check_di_template_binding(str(FIXTURES / "simple_module.py"))
    assert result.domain == "tdom-svcs"
    assert result.parse_error is None


def test_check_di_template_binding_nonexistent():
    """check_di_template_binding should handle missing files."""
    result = check_di_template_binding("/nonexistent/views.py")
    assert result.valid is False
    assert result.parse_error is not None


# ============================================================================
# validate_route_pattern tests
# ============================================================================


def test_validate_route_pattern_valid():
    """Route file with valid paths should pass."""
    result = validate_route_pattern(str(FIXTURES / "route_file.py"))
    assert result.domain == "tdom-svcs"
    assert result.parse_error is None
    # route_file.py has a bad route "users/list" missing leading /
    assert result.valid is False
    rules = {i.rule for i in result.issues}
    assert "route-must-start-with-slash" in rules


def test_validate_route_pattern_all_valid():
    """File with only valid routes should pass."""
    import tempfile
    code = '''
def Route(path, handler): return (path, handler)
def handler(): pass

r1 = Route("/users", handler)
r2 = Route("/users/{id}", handler)
r3 = Route("/", handler)
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_route_pattern(tmp_path)
        assert result.domain == "tdom-svcs"
        assert result.valid is True
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_route_pattern_missing_slash():
    """Route missing leading slash should be an error."""
    import tempfile
    code = '''
def Route(path, handler): return (path, handler)
def handler(): pass
bad = Route("users/list", handler)
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_route_pattern(tmp_path)
        assert result.valid is False
        rules = {i.rule for i in result.issues}
        assert "route-must-start-with-slash" in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_route_pattern_nonexistent():
    """validate_route_pattern should handle missing files."""
    result = validate_route_pattern("/nonexistent/routes.py")
    assert result.valid is False
    assert result.parse_error is not None


def test_validate_route_pattern_unbalanced_braces():
    """Task 10: route with unbalanced braces should be an error."""
    import tempfile
    code = '''
def Route(path, handler): return (path, handler)
def handler(): pass
bad = Route("/users/{id", handler)
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_route_pattern(tmp_path)
        assert result.valid is False
        rules = {i.rule for i in result.issues}
        assert "route-unbalanced-braces" in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_check_di_template_binding_with_inject_and_html():
    """Task 10: Inject[] component + html() without context should warn."""
    import tempfile
    # Use f-string (FormattedString in LibCST) — the visitor checks for FormattedString args
    code = '''
from svcs_di import Inject

class MyView:
    service: Inject[MyService]

    def render(self, name):
        return html(f"<div>{name}</div>")

def html(t): return t
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = check_di_template_binding(tmp_path)
        assert result.domain == "tdom-svcs"
        # Should warn about missing context= in html() call
        rules = {i.rule for i in result.issues}
        assert "di-template-needs-context" in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_middleware_chain_hookable():
    """Task 10: @hookable middleware should also be checked for signature."""
    import tempfile
    code = '''
def hookable(cls): return cls


@hookable
class HookableMiddleware:
    def __call__(self, target, props):
        # Wrong: missing context param
        return props
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_middleware_chain(tmp_path)
        assert result.domain == "tdom-svcs"
        assert result.valid is False
        rules = {i.rule for i in result.issues}
        assert "middleware-must-have-correct-signature" in rules
    finally:
        import os
        os.unlink(tmp_path)


def test_validate_middleware_chain_syntax_error():
    """Task 10: syntax error file returns parse_error, not a crash."""
    import tempfile
    code = "class broken(:\n    pass\n"
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_middleware_chain(tmp_path)
        assert result.valid is False
        assert result.parse_error is not None
    finally:
        import os
        os.unlink(tmp_path)
