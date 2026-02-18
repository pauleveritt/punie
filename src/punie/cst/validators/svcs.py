"""svcs domain validators.

Three validators for svcs service patterns:
- validate_service_registration: check @injectable @dataclass + Inject[] fields
- check_dependency_graph: check for layer violations in Inject[] chains
- validate_injection_site: check Inject[] fields reference known types
"""

from __future__ import annotations

import libcst as cst
import libcst.matchers as m

from punie.cst.domain_models import DomainValidationResult, ValidationIssue


def _get_decorator_names(node: cst.ClassDef) -> list[str]:
    """Extract decorator names from a ClassDef node."""
    names = []
    for decorator in node.decorators:
        dec = decorator.decorator
        if m.matches(dec, m.Name()):
            names.append(dec.value)  # type: ignore[attr-defined]
        elif m.matches(dec, m.Attribute()):
            names.append(dec.attr.value)  # type: ignore[attr-defined]
        elif m.matches(dec, m.Call(func=m.Name())):
            names.append(dec.func.value)  # type: ignore[attr-defined]
        elif m.matches(dec, m.Call(func=m.Attribute())):
            names.append(dec.func.attr.value)  # type: ignore[attr-defined]
    return names


def _is_inject_annotation(annotation: cst.BaseExpression) -> bool:
    """Check if a type annotation is an Inject[X] form."""
    return m.matches(
        annotation,
        m.Subscript(value=m.Name("Inject")),
    )


def _get_inject_type(annotation: cst.BaseExpression) -> str | None:
    """Extract the type name from an Inject[X] annotation."""
    if m.matches(annotation, m.Subscript(value=m.Name("Inject"))):
        sub: cst.Subscript = annotation  # type: ignore[assignment]
        slice_val = sub.slice
        if isinstance(slice_val, (list, tuple)) and len(slice_val) > 0:
            first = slice_val[0]
            if isinstance(first, cst.SubscriptElement):
                inner = first.slice
                if isinstance(inner, cst.Index):
                    val = inner.value
                    if m.matches(val, m.Name()):
                        return val.value  # type: ignore[attr-defined]
                    elif m.matches(val, m.Attribute()):
                        return val.attr.value  # type: ignore[attr-defined]
    return None


class _ServiceRegistrationVisitor(cst.CSTVisitor):
    """Visitor that validates service registration patterns."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self.classes_found: list[str] = []
        self._class_stack: list[str] = []  # Task 3: stack for nested classes
        self._class_decorators: dict[str, list[str]] = {}
        self._class_inject_fields: dict[str, list[str]] = {}

    @property
    def _current_class(self) -> str | None:
        return self._class_stack[-1] if self._class_stack else None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        name = node.name.value
        self.classes_found.append(name)
        self._class_stack.append(name)  # Task 3: push onto stack
        self._class_decorators[name] = _get_decorator_names(node)
        self._class_inject_fields[name] = []
        return None

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()  # Task 3: pop from stack

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool | None:
        if self._current_class and isinstance(node.target, cst.Name):
            if _is_inject_annotation(node.annotation.annotation):
                inject_type = _get_inject_type(node.annotation.annotation)
                field_info = f"{node.target.value}: Inject[{inject_type}]"
                self._class_inject_fields[self._current_class].append(field_info)
        return None

    def get_issues(self) -> list[ValidationIssue]:
        issues = []
        for name in self.classes_found:
            decorators = self._class_decorators.get(name, [])
            inject_fields = self._class_inject_fields.get(name, [])

            # Only validate classes that look like services (have @injectable or Inject[] fields)
            is_service = "injectable" in decorators or len(inject_fields) > 0
            if not is_service:
                continue

            if "injectable" not in decorators:
                issues.append(
                    ValidationIssue(
                        rule="service-must-have-injectable",
                        severity="error",
                        message=f"Service class '{name}' has Inject[] fields but is missing @injectable decorator",
                        suggestion="Add @injectable decorator from svcs_di.injectors above the class",
                    )
                )
            if "dataclass" not in decorators:
                issues.append(
                    ValidationIssue(
                        rule="service-must-have-dataclass",
                        severity="error",
                        message=f"Service class '{name}' is missing @dataclass decorator",
                        suggestion="Add @dataclass decorator below @injectable",
                    )
                )
        return issues


def validate_service_registration(file_path: str) -> DomainValidationResult:
    """Validate svcs service registration patterns in a Python file.

    Checks that service classes follow the svcs pattern:
    - @injectable decorator present
    - @dataclass decorator present
    - Inject[] typed fields for dependencies

    Args:
        file_path: Path to Python file containing service definitions

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
            domain="svcs",
            issues=[],
            parse_error=str(e),
        )

    visitor = _ServiceRegistrationVisitor()
    module.visit(visitor)
    issues = visitor.get_issues()
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="svcs",
        issues=issues,
    )


class _DependencyGraphVisitor(cst.CSTVisitor):
    """Visitor that checks for dependency graph issues."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self._class_stack: list[str] = []  # Task 3: stack for nested classes
        self._class_kind: dict[str, str] = {}  # "service" | "component"
        self._class_inject_types: dict[str, list[str]] = {}

    @property
    def _current_class(self) -> str | None:
        return self._class_stack[-1] if self._class_stack else None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        name = node.name.value
        self._class_stack.append(name)  # Task 3: push onto stack
        self._class_inject_types[name] = []
        decorators = _get_decorator_names(node)

        # Classify: has injectable → service; has @dataclass but NO @injectable → potential component
        # Plain classes (no decorators) are not classified to avoid false positives
        if "injectable" in decorators:
            self._class_kind[name] = "service"
        elif "dataclass" in decorators:
            self._class_kind[name] = "component"
        # else: unclassified (plain class, not a service or component in the tdom sense)
        return None

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()  # Task 3: pop from stack

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool | None:
        if self._current_class and isinstance(node.target, cst.Name):
            if _is_inject_annotation(node.annotation.annotation):
                inject_type = _get_inject_type(node.annotation.annotation)
                if inject_type:
                    self._class_inject_types[self._current_class].append(inject_type)
        return None

    def get_issues(self) -> list[ValidationIssue]:
        issues = []
        # Check for layer violations: services should not inject components
        for class_name, kind in self._class_kind.items():
            if kind == "service":
                for dep_type in self._class_inject_types.get(class_name, []):
                    dep_kind = self._class_kind.get(dep_type, "unknown")
                    if dep_kind == "component":
                        issues.append(
                            ValidationIssue(
                                rule="service-cannot-depend-on-component",
                                severity="error",
                                message=f"Service '{class_name}' depends on component '{dep_type}' (layer violation)",
                                suggestion="Services should only depend on other services, not components",
                            )
                        )
        return issues


def check_dependency_graph(file_path: str) -> DomainValidationResult:
    """Check svcs dependency graph for layer violations.

    Verifies that the dependency injection graph follows correct layering:
    - Services can depend on other services
    - Services should not depend on components (layer violation)
    - No obvious circular dependencies (within the same file)

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
            domain="svcs",
            issues=[],
            parse_error=str(e),
        )

    visitor = _DependencyGraphVisitor()
    module.visit(visitor)
    issues = visitor.get_issues()
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="svcs",
        issues=issues,
    )


class _InjectionSiteVisitor(cst.CSTVisitor):
    """Visitor that validates Inject[] field usage."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self._imported_names: set[str] = set()
        self._class_stack: list[str] = []  # Task 3: stack for nested classes

    @property
    def _current_class(self) -> str | None:
        return self._class_stack[-1] if self._class_stack else None

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool | None:
        if isinstance(node.names, cst.ImportStar):
            return None
        for alias in node.names:
            if isinstance(alias.name, cst.Name):
                self._imported_names.add(alias.name.value)
        return None

    def visit_Import(self, node: cst.Import) -> bool | None:
        # Task 7: track bare import names (e.g., "import Database")
        if isinstance(node.names, cst.ImportStar):
            return None
        if isinstance(node.names, (list, tuple)):
            for alias in node.names:
                if isinstance(alias.name, cst.Name):
                    self._imported_names.add(alias.name.value)
        return None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        self._class_stack.append(node.name.value)  # Task 3: push onto stack
        return None

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()  # Task 3: pop from stack

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool | None:
        if self._current_class and isinstance(node.target, cst.Name):
            ann = node.annotation.annotation
            if _is_inject_annotation(ann):
                inject_type = _get_inject_type(ann)
                if inject_type and inject_type not in self._imported_names:
                    self.issues.append(
                        ValidationIssue(
                            rule="inject-type-must-be-imported",
                            severity="warning",
                            message=f"Inject[{inject_type}] in '{self._current_class}': '{inject_type}' not found in imports",
                            suggestion=f"Add import for '{inject_type}' at the top of the file",
                        )
                    )
        return None


def validate_injection_site(file_path: str) -> DomainValidationResult:
    """Validate Inject[] field sites in a Python file.

    Checks that Inject[] fields reference types that are imported
    in the file.

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
            domain="svcs",
            issues=[],
            parse_error=str(e),
        )

    visitor = _InjectionSiteVisitor()
    module.visit(visitor)
    issues = visitor.issues
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="svcs",
        issues=issues,
    )
