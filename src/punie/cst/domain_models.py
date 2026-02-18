"""Domain Pydantic models for tdom-svcs pattern validation.

These models describe the vocabulary used by the domain validators:
- ComponentSpec: tdom component (@dataclass + __call__ -> Node)
- ServiceRegistration: svcs service (@injectable @dataclass + Inject[])
- MiddlewareSpec: tdom-svcs middleware (@middleware or @hookable)
- ValidationIssue: a single finding from a validator
- DomainValidationResult: shared result type for all validators

Note:
    ComponentSpec, ServiceRegistration, and MiddlewareSpec are not
    currently used by the validators. They are intended as structured
    vocabulary for Phase 33 training data generation — each validator
    could emit these rich specs for fine-tuning the model's domain
    knowledge.
"""

from pydantic import BaseModel


class ComponentSpec(BaseModel):
    """A tdom component: @dataclass with __call__() -> Node.

    Attributes:
        name: Class name
        has_dataclass_decorator: True if @dataclass is present
        has_callable: True if __call__ method exists
        return_type: Return type annotation of __call__ (should be "Node")
        uses_html_t_string: True if html(t"...") pattern detected
        inject_fields: Names of Inject[X] typed fields
        props: Names of plain fields (non-Inject)
        has_injectable_decorator: True if @injectable present (for scan)
    """

    name: str
    has_dataclass_decorator: bool
    has_callable: bool
    return_type: str | None
    uses_html_t_string: bool
    inject_fields: list[str]
    props: list[str]
    has_injectable_decorator: bool


class ServiceRegistration(BaseModel):
    """An svcs service: @injectable @dataclass with Inject[] fields.

    Attributes:
        name: Class name
        has_injectable_decorator: True if @injectable present
        has_dataclass_decorator: True if @dataclass present
        inject_dependencies: Names of Inject[X] fields
        lifecycle: "request" | "session" | "app" (inferred from context)
    """

    name: str
    has_injectable_decorator: bool
    has_dataclass_decorator: bool
    inject_dependencies: list[str]
    lifecycle: str


class MiddlewareSpec(BaseModel):
    """A tdom-svcs middleware: @middleware or @hookable.

    Attributes:
        name: Class name
        middleware_type: "global" (@middleware) | "per_target" (@hookable) | "injectable" (@injectable)
        categories: Category list from @middleware(categories=[...])
        priority: Value of priority field (int) or None if absent
        has_correct_signature: True if __call__(self, target, props, context) present
    """

    name: str
    middleware_type: str
    categories: list[str]
    priority: int | None
    has_correct_signature: bool


class ValidationIssue(BaseModel):
    """A single validation finding from a domain validator.

    Attributes:
        rule: Rule identifier (e.g., "component-must-return-node")
        severity: "error" | "warning"
        message: Human-readable description of the issue
        line: Line number in source file (1-based, optional)
        suggestion: Suggested fix (optional)
    """

    rule: str
    severity: str
    message: str
    line: int | None = None
    suggestion: str | None = None


class DomainValidationResult(BaseModel):
    """Shared result type for all domain validators.

    Attributes:
        valid: True if no errors found (warnings allowed)
        domain: Which validator family produced this ("tdom" | "svcs" | "tdom-svcs")
        issues: List of validation findings
        parse_error: Error message if LibCST failed to parse the file
    """

    valid: bool
    domain: str
    issues: list[ValidationIssue]
    parse_error: str | None = None
