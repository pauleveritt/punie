"""tdom domain validators.

Three validators for tdom component patterns:
- validate_component: check @dataclass + __call__ -> Node + html() patterns
- check_render_tree: check component composition and references
- validate_escape_context: check for unsafe f-strings in html() calls
"""

from __future__ import annotations

from typing import Any

import libcst as cst
import libcst.matchers as m

from punie.cst.domain_models import DomainValidationResult, ValidationIssue


class _ComponentVisitor(cst.CSTVisitor):
    """Visitor that collects component validation findings."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self.classes_found: list[str] = []
        self._class_stack: list[str] = []  # Task 3: stack to handle nested classes
        self._class_has_dataclass: dict[str, bool] = {}
        self._class_has_injectable: dict[str, bool] = {}
        self._class_has_callable: dict[str, bool] = {}
        self._class_callable_returns_node: dict[str, bool] = {}
        self._class_uses_html: dict[str, bool] = {}
        self._class_has_fstring_in_html: dict[str, bool] = {}

    @property
    def _current_class(self) -> str | None:
        return self._class_stack[-1] if self._class_stack else None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        name = node.name.value
        self.classes_found.append(name)
        self._class_stack.append(name)  # Task 3: push onto stack
        self._class_has_dataclass[name] = False
        self._class_has_injectable[name] = False
        self._class_has_callable[name] = False
        self._class_callable_returns_node[name] = False
        self._class_uses_html[name] = False
        self._class_has_fstring_in_html[name] = False

        for decorator in node.decorators:
            dec = decorator.decorator
            if m.matches(dec, m.Name("dataclass")):
                self._class_has_dataclass[name] = True
            elif m.matches(dec, m.Name("injectable")):
                self._class_has_injectable[name] = True
            elif m.matches(dec, m.Attribute(attr=m.Name("dataclass"))):
                self._class_has_dataclass[name] = True
            elif m.matches(dec, m.Attribute(attr=m.Name("injectable"))):
                self._class_has_injectable[name] = True
            # Task 2: handle call forms @dataclass() and @dataclass(frozen=True)
            elif m.matches(dec, m.Call(func=m.Name("dataclass"))):
                self._class_has_dataclass[name] = True
            elif m.matches(dec, m.Call(func=m.Name("injectable"))):
                self._class_has_injectable[name] = True
            elif m.matches(dec, m.Call(func=m.Attribute(attr=m.Name("dataclass")))):
                self._class_has_dataclass[name] = True
            elif m.matches(dec, m.Call(func=m.Attribute(attr=m.Name("injectable")))):
                self._class_has_injectable[name] = True
        return None

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()  # Task 3: pop from stack

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:
        if self._current_class and node.name.value == "__call__":
            self._class_has_callable[self._current_class] = True
            # Check return type
            if node.returns is not None:
                ann = node.returns.annotation
                if m.matches(ann, m.Name("Node")):
                    self._class_callable_returns_node[self._current_class] = True
        return None

    def visit_Call(self, node: cst.Call) -> bool | None:
        if self._current_class and m.matches(node.func, m.Name("html")):
            self._class_uses_html[self._current_class] = True
            # Check for f-strings in arguments (unsafe pattern)
            for arg in node.args:
                if m.matches(arg.value, m.FormattedString()):
                    fs: Any = arg.value
                    # f-strings start with 'f"' or "f'", t-strings start with 't"' or "t'"
                    if hasattr(fs, "start") and fs.start.lower().startswith("f"):
                        self._class_has_fstring_in_html[self._current_class] = True
        return None

    def get_issues(self) -> list[ValidationIssue]:
        issues = []
        for name in self.classes_found:
            # Task 1: skip classes with no component signal (helper, exception, mixin)
            is_component = (
                self._class_has_dataclass.get(name, False)
                or self._class_has_callable.get(name, False)
                or self._class_uses_html.get(name, False)
            )
            if not is_component:
                continue
            if not self._class_has_dataclass.get(name, False):
                issues.append(
                    ValidationIssue(
                        rule="component-must-have-dataclass",
                        severity="error",
                        message=f"Class '{name}' is missing @dataclass decorator",
                        suggestion="Add @dataclass decorator above the class definition",
                    )
                )
            if not self._class_has_callable.get(name, False):
                issues.append(
                    ValidationIssue(
                        rule="component-must-have-callable",
                        severity="error",
                        message=f"Class '{name}' is missing __call__ method",
                        suggestion="Add def __call__(self) -> Node: method",
                    )
                )
            elif not self._class_callable_returns_node.get(name, False):
                issues.append(
                    ValidationIssue(
                        rule="component-callable-must-return-node",
                        severity="warning",
                        message=f"Class '{name}' __call__ does not annotate return type as Node",
                        suggestion="Add -> Node return type annotation to __call__",
                    )
                )
            if self._class_has_fstring_in_html.get(name, False):
                issues.append(
                    ValidationIssue(
                        rule="component-no-fstring-in-html",
                        severity="error",
                        message=f"Class '{name}' uses f-string in html() call (XSS risk)",
                        suggestion="Use t-string (t\"...\") instead of f-string in html()",
                    )
                )
        return issues


def validate_component(file_path: str) -> DomainValidationResult:
    """Validate tdom component patterns in a Python file.

    Checks that classes follow the tdom component pattern:
    - @dataclass decorator present
    - __call__ method exists and returns Node
    - html() calls use t-strings, not f-strings

    Args:
        file_path: Path to Python file containing component definitions

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
            domain="tdom",
            issues=[],
            parse_error=str(e),
        )

    visitor = _ComponentVisitor()
    module.visit(visitor)
    issues = visitor.get_issues()
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="tdom",
        issues=issues,
    )


class _RenderTreeVisitor(cst.CSTVisitor):
    """Visitor that checks component composition patterns."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self._html_calls: list[cst.Call] = []
        self._imported_names: set[str] = set()

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool | None:
        if isinstance(node.names, cst.ImportStar):
            return None
        for alias in node.names:
            if isinstance(alias.name, cst.Name):
                self._imported_names.add(alias.name.value)
            elif isinstance(alias.name, cst.Attribute):
                self._imported_names.add(alias.name.attr.value)
        return None

    def visit_Import(self, node: cst.Import) -> bool | None:
        if isinstance(node.names, cst.ImportStar):
            return None
        if isinstance(node.names, (list, tuple)):
            for alias in node.names:
                if isinstance(alias.name, cst.Name):
                    self._imported_names.add(alias.name.value)
        return None

    def get_issues(self) -> list[ValidationIssue]:
        return self.issues


def check_render_tree(file_path: str) -> DomainValidationResult:
    """Check component render tree composition in a Python file.

    Verifies that component compositions follow tdom patterns:
    - Components referenced in html() are importable
    - No obvious dangling references

    Args:
        file_path: Path to Python file to analyze

    Returns:
        DomainValidationResult with issues list

    Note:
        TODO: This is a placeholder implementation. The visitor currently
        collects import names but does not cross-reference them against
        component usages. Full render tree validation is planned for
        a future phase.
    """
    try:
        with open(file_path) as f:
            source = f.read()
        module = cst.parse_module(source)
    except Exception as e:
        return DomainValidationResult(
            valid=False,
            domain="tdom",
            issues=[],
            parse_error=str(e),
        )

    visitor = _RenderTreeVisitor()
    module.visit(visitor)
    issues = visitor.get_issues()
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="tdom",
        issues=issues,
    )


class _EscapeContextVisitor(cst.CSTVisitor):
    """Visitor that checks for unsafe string usage in html() calls."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self._in_html_call = False

    def visit_Call(self, node: cst.Call) -> bool | None:
        if m.matches(node.func, m.Name("html")):
            for arg in node.args:
                val = arg.value
                if m.matches(val, m.FormattedString()):
                    fs: Any = val
                    if hasattr(fs, "start") and fs.start.lower().startswith("f"):
                        self.issues.append(
                            ValidationIssue(
                                rule="no-fstring-in-html",
                                severity="error",
                                message="F-string passed to html() is unsafe (XSS risk)",
                                suggestion="Use t-string: html(t\"...\") instead of html(f\"...\")",
                            )
                        )
        return None


def validate_escape_context(file_path: str) -> DomainValidationResult:
    """Validate that html() calls use safe string patterns.

    Checks that html() calls do not use raw f-strings which are
    susceptible to XSS. T-strings (t"...") provide auto-escaping.

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
            domain="tdom",
            issues=[],
            parse_error=str(e),
        )

    visitor = _EscapeContextVisitor()
    module.visit(visitor)
    issues = visitor.issues
    errors = [i for i in issues if i.severity == "error"]
    return DomainValidationResult(
        valid=len(errors) == 0,
        domain="tdom",
        issues=issues,
    )
