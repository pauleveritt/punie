"""Tests for svcs domain validators."""

from pathlib import Path

import pytest

libcst = pytest.importorskip("libcst")

from punie.cst.validators.svcs import (  # noqa: E402
    check_dependency_graph,
    validate_injection_site,
    validate_service_registration,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cst"


# ============================================================================
# validate_service_registration tests
# ============================================================================


def test_validate_service_registration_valid():
    """Valid service should pass registration validation."""
    result = validate_service_registration(str(FIXTURES / "valid_service.py"))
    assert result.domain == "svcs"
    assert result.parse_error is None
    assert result.valid is True


def test_validate_service_registration_invalid():
    """Invalid service (missing @injectable) should fail."""
    result = validate_service_registration(str(FIXTURES / "invalid_service.py"))
    assert result.domain == "svcs"
    assert result.parse_error is None
    assert result.valid is False
    rules = {i.rule for i in result.issues}
    assert "service-must-have-injectable" in rules


def test_validate_service_registration_nonexistent():
    """validate_service_registration should handle missing files."""
    result = validate_service_registration("/nonexistent/services.py")
    assert result.valid is False
    assert result.parse_error is not None


def test_validate_service_registration_error_severity():
    """Missing @injectable should be an error, not a warning."""
    result = validate_service_registration(str(FIXTURES / "invalid_service.py"))
    errors = [i for i in result.issues if i.severity == "error"]
    assert len(errors) > 0


def test_validate_service_registration_has_suggestions():
    """Service validation issues should include suggestions."""
    result = validate_service_registration(str(FIXTURES / "invalid_service.py"))
    for issue in result.issues:
        if issue.severity == "error":
            assert issue.suggestion is not None


def test_validate_service_no_classes():
    """File with no classes should be valid (nothing to check)."""
    import tempfile
    code = "# Just a module\nx = 1\n"
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_service_registration(tmp_path)
        assert result.valid is True
        assert result.issues == []
    finally:
        import os
        os.unlink(tmp_path)


# ============================================================================
# check_dependency_graph tests
# ============================================================================


def test_check_dependency_graph_valid_service():
    """Valid service with service dependencies should pass."""
    result = check_dependency_graph(str(FIXTURES / "valid_service.py"))
    assert result.domain == "svcs"
    assert result.parse_error is None
    # No layer violations in valid_service.py (Database has no Inject fields)
    assert result.valid is True


def test_check_dependency_graph_nonexistent():
    """check_dependency_graph should handle missing files."""
    result = check_dependency_graph("/nonexistent/services.py")
    assert result.valid is False
    assert result.parse_error is not None


def test_check_dependency_graph_layer_violation():
    """Service depending on component should be a layer violation."""
    import tempfile
    code = '''
from dataclasses import dataclass
from svcs_di import Inject
from svcs_di.injectors import injectable


@dataclass
class UIComponent:
    """A component (no @injectable)."""
    title: str = "Hello"

    def __call__(self):
        return self.title


@injectable
@dataclass
class BadService:
    """Service that wrongly depends on a component."""
    component: Inject[UIComponent]
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = check_dependency_graph(tmp_path)
        assert result.domain == "svcs"
        # Should detect the layer violation
        rules = {i.rule for i in result.issues}
        assert "service-cannot-depend-on-component" in rules
    finally:
        import os
        os.unlink(tmp_path)


# ============================================================================
# validate_injection_site tests
# ============================================================================


def test_validate_injection_site_valid():
    """Service with imported Inject types should pass."""
    result = validate_injection_site(str(FIXTURES / "valid_service.py"))
    assert result.domain == "svcs"
    assert result.parse_error is None


def test_validate_injection_site_nonexistent():
    """validate_injection_site should handle missing files."""
    result = validate_injection_site("/nonexistent/file.py")
    assert result.valid is False
    assert result.parse_error is not None


def test_validate_injection_site_missing_import():
    """Inject[X] with unimported type should generate a warning."""
    import tempfile
    code = '''
from dataclasses import dataclass
from svcs_di import Inject
from svcs_di.injectors import injectable


@injectable
@dataclass
class MyService:
    """Service with unimported dep."""
    db: Inject[UnimportedDatabase]  # UnimportedDatabase not imported!
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = validate_injection_site(tmp_path)
        assert result.domain == "svcs"
        rules = {i.rule for i in result.issues}
        assert "inject-type-must-be-imported" in rules
    finally:
        import os
        os.unlink(tmp_path)
