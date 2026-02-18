"""Tests for domain Pydantic models."""

from punie.cst.domain_models import (
    ComponentSpec,
    DomainValidationResult,
    MiddlewareSpec,
    ServiceRegistration,
    ValidationIssue,
)


def test_validation_issue_construction():
    """ValidationIssue should be constructable with required fields."""
    issue = ValidationIssue(
        rule="component-must-have-dataclass",
        severity="error",
        message="Missing @dataclass",
    )
    assert issue.rule == "component-must-have-dataclass"
    assert issue.severity == "error"
    assert issue.message == "Missing @dataclass"
    assert issue.line is None
    assert issue.suggestion is None


def test_validation_issue_with_optional_fields():
    """ValidationIssue should accept optional line and suggestion."""
    issue = ValidationIssue(
        rule="component-must-return-node",
        severity="warning",
        message="__call__ should return Node",
        line=42,
        suggestion="Add -> Node return annotation",
    )
    assert issue.line == 42
    assert issue.suggestion == "Add -> Node return annotation"


def test_domain_validation_result_valid():
    """DomainValidationResult should represent a valid result."""
    result = DomainValidationResult(
        valid=True,
        domain="tdom",
        issues=[],
    )
    assert result.valid is True
    assert result.domain == "tdom"
    assert result.issues == []
    assert result.parse_error is None


def test_domain_validation_result_invalid():
    """DomainValidationResult should represent an invalid result with issues."""
    issue = ValidationIssue(
        rule="test-rule",
        severity="error",
        message="Test error",
    )
    result = DomainValidationResult(
        valid=False,
        domain="svcs",
        issues=[issue],
    )
    assert result.valid is False
    assert len(result.issues) == 1
    assert result.issues[0].rule == "test-rule"


def test_domain_validation_result_parse_error():
    """DomainValidationResult should hold a parse error."""
    result = DomainValidationResult(
        valid=False,
        domain="tdom",
        issues=[],
        parse_error="SyntaxError: invalid syntax",
    )
    assert result.parse_error == "SyntaxError: invalid syntax"


def test_component_spec_construction():
    """ComponentSpec should be constructable."""
    spec = ComponentSpec(
        name="Greeting",
        has_dataclass_decorator=True,
        has_callable=True,
        return_type="Node",
        uses_html_t_string=True,
        inject_fields=["users: Inject[Users]"],
        props=["title"],
        has_injectable_decorator=False,
    )
    assert spec.name == "Greeting"
    assert spec.has_dataclass_decorator is True
    assert spec.return_type == "Node"
    assert len(spec.inject_fields) == 1


def test_service_registration_construction():
    """ServiceRegistration should be constructable."""
    reg = ServiceRegistration(
        name="UserService",
        has_injectable_decorator=True,
        has_dataclass_decorator=True,
        inject_dependencies=["db: Inject[Database]"],
        lifecycle="request",
    )
    assert reg.name == "UserService"
    assert reg.has_injectable_decorator is True


def test_middleware_spec_construction():
    """MiddlewareSpec should be constructable."""
    spec = MiddlewareSpec(
        name="AuthMiddleware",
        middleware_type="global",
        categories=["security", "auth"],
        priority=-20,
        has_correct_signature=True,
    )
    assert spec.name == "AuthMiddleware"
    assert spec.categories == ["security", "auth"]
    assert spec.priority == -20
    assert spec.has_correct_signature is True


def test_middleware_spec_no_priority():
    """MiddlewareSpec should allow None priority."""
    spec = MiddlewareSpec(
        name="SimpleMiddleware",
        middleware_type="global",
        categories=["logging"],
        priority=None,
        has_correct_signature=True,
    )
    assert spec.priority is None


def test_domain_validation_result_json_serializable():
    """DomainValidationResult should serialize to JSON via Pydantic."""
    issue = ValidationIssue(
        rule="test-rule",
        severity="error",
        message="Test",
        line=5,
    )
    result = DomainValidationResult(
        valid=False,
        domain="tdom",
        issues=[issue],
    )
    json_str = result.model_dump_json()
    assert '"valid":false' in json_str or '"valid": false' in json_str
    assert "test-rule" in json_str
