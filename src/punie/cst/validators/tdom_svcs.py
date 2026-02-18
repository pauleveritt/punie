"""tdom-svcs domain validators.

Three validators for tdom-svcs middleware/integration patterns:
- validate_middleware_chain: check @middleware + categories + __call__ signature
- check_di_template_binding: check html() context parameter for DI components
- validate_route_pattern: check route patterns are syntactically valid
"""

from __future__ import annotations

import libcst as cst
import libcst.matchers as m

from punie.cst.domain_models import DomainValidationResult, ValidationIssue


def _get_decorator_names_and_calls(
    node: cst.ClassDef,
) -> list[tuple[str, cst.BaseExpression]]:
    """Extract (name, node) pairs for all decorators."""
    result = []
    for decorator in node.decorators:
        dec = decorator.decorator
        if m.matches(dec, m.Name()):
            result.append((dec.value, dec))  # type: ignore[attr-defined]
        elif m.matches(dec, m.Attribute()):
            result.append((dec.attr.value, dec))  # type: ignore[attr-defined]
        elif m.matches(dec, m.Call(func=m.Name())):
            result.append((dec.func.value, dec))  # type: ignore[attr-defined]
        elif m.matches(dec, m.Call(func=m.Attribute())):
            result.append((dec.func.attr.value, dec))  # type: ignore[attr-defined]
    return result


def _get_middleware_categories(decorator: cst.BaseExpression) -> list[str]:
    """Extract categories from @middleware(categories=[...]) decorator."""
    categories = []
    if not m.matches(decorator, m.Call()):
        return categories

    call: cst.Call = decorator  # type: ignore[assignment]
    for arg in call.args:
        if (
            arg.keyword is not None
            and arg.keyword.value == "categories"
            and m.matches(arg.value, m.List())
        ):
            lst: cst.List = arg.value  # type: ignore[assignment]
            for element in lst.elements:
                if m.matches(element.value, m.SimpleString()):
                    raw = element.value.value  # type: ignore[attr-defined]
                    categories.append(raw.strip("\"'"))
                elif m.matches(element.value, m.FormattedString()):
                    pass  # Skip dynamic values
    return categories


def _has_correct_middleware_signature(node: cst.ClassDef) -> bool:
    """Check if class has __call__(self, target, props, context) method."""
    for statement in node.body.body:
        if (
            isinstance(statement, cst.SimpleStatementLine)
            or not isinstance(statement, cst.FunctionDef)
        ):
            continue
        func: cst.FunctionDef = statement  # type: ignore[assignment]
        if func.name.value != "__call__":
            continue
        params = func.params
        param_names = [p.name.value for p in params.params]
        return param_names == ["self", "target", "props", "context"]
    return False



class _MiddlewareChainVisitor(cst.CSTVisitor):
    """Visitor that validates middleware class patterns."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        name = node.name.value
        dec_info = _get_decorator_names_and_calls(node)
        dec_names = [n for n, _ in dec_info]

        # Only check classes with @middleware or @hookable
        is_middleware = "middleware" in dec_names
        is_hookable = "hookable" in dec_names
        # Task 4: use proper isinstance check instead of fragile str() search
        is_injectable_middleware = "injectable" in dec_names and any(
            isinstance(s, cst.FunctionDef) and s.name.value == "__call__"
            for s in node.body.body
        )

        if not (is_middleware or is_hookable or is_injectable_middleware):
            return None

        # Find the decorator node for @middleware
        middleware_dec = None
        for dec_name, dec_node in dec_info:
            if dec_name == "middleware":
                middleware_dec = dec_node
                break

        if is_middleware and middleware_dec is not None:
            categories = _get_middleware_categories(middleware_dec)
            if not categories:
                self.issues.append(
                    ValidationIssue(
                        rule="middleware-must-have-categories",
                        severity="warning",
                        message=f"Middleware '{name}' uses @middleware without categories",
                        suggestion="Add categories=[...] to @middleware decorator",
                    )
                )

        if not _has_correct_middleware_signature(node):
            self.issues.append(
                ValidationIssue(
                    rule="middleware-must-have-correct-signature",
                    severity="error",
                    message=f"Middleware '{name}' __call__ must have signature (self, target, props, context)",
                    suggestion="Define: def __call__(self, target, props, context)",
                )
            )
        return None


def validate_middleware_chain(file_path: str) -> DomainValidationResult:
    """Validate tdom-svcs middleware patterns in a Python file.

    Checks that middleware classes follow the tdom-svcs pattern:
    - @middleware has categories list
    - __call__ has correct (self, target, props, context) signature
    - @injectable middleware has proper DI setup

    Args:
        file_path: Path to Python file containing middleware definitions

    Returns:
        DomainValidationResult with issues list
    """
    try:
        with open(file_path) as f:
            source = f.read()
        module = cst.parse_module(source)
    except Exception as e:
        return DomainValidationResult(
            valid=False,
            domain="tdom-svcs",
            issues=[],
            parse_error=str(e),
        )

    visitor = _MiddlewareChainVisitor()
    module.visit(visitor)
    issues = visitor.issues
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="tdom-svcs",
        issues=issues,
    )


class _DITemplateBindingVisitor(cst.CSTVisitor):
    """Visitor that checks DI context passing in html() calls."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self._inject_components: set[str] = set()
        self._class_stack: list[str] = []  # Task 3: stack for nested classes

    @property
    def _current_class(self) -> str | None:
        return self._class_stack[-1] if self._class_stack else None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        name = node.name.value
        self._class_stack.append(name)  # Task 3: push onto stack
        # Check if this class has any Inject[] fields
        for statement in node.body.body:
            if isinstance(statement, cst.SimpleStatementLine):
                for item in statement.body:
                    if isinstance(item, cst.AnnAssign) and isinstance(
                        item.target, cst.Name
                    ):
                        if m.matches(
                            item.annotation.annotation,
                            m.Subscript(value=m.Name("Inject")),
                        ):
                            self._inject_components.add(name)
        return None

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()  # Task 3: pop from stack

    def visit_Call(self, node: cst.Call) -> bool | None:
        # Check html() calls that reference Inject[] components
        if not m.matches(node.func, m.Name("html")):
            return None

        # Look for component references (heuristic: html(t"<{Comp} />"))
        # Check if context keyword is passed
        has_context = any(
            arg.keyword is not None and arg.keyword.value == "context"
            for arg in node.args
        )

        # Check if any arg looks like a component reference
        # (This is a simple heuristic - full analysis would require type checking)
        for arg in node.args:
            val = arg.value
            if m.matches(val, m.FormattedString()):
                # Template string - check if it contains component references
                # If not passing context, and it looks like it renders components, warn
                if not has_context and self._inject_components:
                    self.issues.append(
                        ValidationIssue(
                            rule="di-template-needs-context",
                            severity="warning",
                            message="html() call may render Inject[] components but no context= passed",
                            suggestion="Add context=container to html() call: html(t\"...\", context=container)",
                        )
                    )
                    break
        return None


def check_di_template_binding(file_path: str) -> DomainValidationResult:
    """Check that DI components have context passed in html() calls.

    Verifies that when Inject[] components are rendered via html(),
    the container context is passed to enable dependency injection.

    Args:
        file_path: Path to Python file to analyze

    Returns:
        DomainValidationResult with issues list
    """
    try:
        with open(file_path) as f:
            source = f.read()
        module = cst.parse_module(source)
    except Exception as e:
        return DomainValidationResult(
            valid=False,
            domain="tdom-svcs",
            issues=[],
            parse_error=str(e),
        )

    visitor = _DITemplateBindingVisitor()
    module.visit(visitor)
    issues = visitor.issues
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="tdom-svcs",
        issues=issues,
    )


class _RoutePatternVisitor(cst.CSTVisitor):
    """Visitor that validates route pattern registrations."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def visit_Call(self, node: cst.Call) -> bool | None:
        # Check for route registration patterns like Route("/path", ...)
        # or add_route("/path", ...)
        if not (
            m.matches(node.func, m.Name("Route"))
            or m.matches(node.func, m.Attribute(attr=m.Name("add_route")))
            or m.matches(node.func, m.Name("add_route"))
        ):
            return None

        # Check first argument is a string (route path)
        if node.args:
            first_arg = node.args[0].value
            if m.matches(first_arg, m.SimpleString()):
                path: str = first_arg.value.strip("\"'")  # type: ignore[attr-defined]
                # Basic validation: path must start with /
                if not path.startswith("/"):
                    self.issues.append(
                        ValidationIssue(
                            rule="route-must-start-with-slash",
                            severity="error",
                            message=f"Route path '{path}' must start with '/'",
                            suggestion=f"Change to '/{path}'",
                        )
                    )
                # Check for balanced braces in path parameters
                if path.count("{") != path.count("}"):
                    self.issues.append(
                        ValidationIssue(
                            rule="route-unbalanced-braces",
                            severity="error",
                            message=f"Route path '{path}' has unbalanced braces in parameter",
                            suggestion="Ensure every { has a matching }",
                        )
                    )
        return None


def validate_route_pattern(file_path: str) -> DomainValidationResult:
    """Validate route patterns in a Python file.

    Checks that route definitions use valid path patterns:
    - Paths start with /
    - Path parameters have balanced braces {{ }}

    Args:
        file_path: Path to Python file containing route definitions

    Returns:
        DomainValidationResult with issues list
    """
    try:
        with open(file_path) as f:
            source = f.read()
        module = cst.parse_module(source)
    except Exception as e:
        return DomainValidationResult(
            valid=False,
            domain="tdom-svcs",
            issues=[],
            parse_error=str(e),
        )

    visitor = _RoutePatternVisitor()
    module.visit(visitor)
    issues = visitor.issues
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="tdom-svcs",
        issues=issues,
    )
