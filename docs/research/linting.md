# Linting as "code tools"

From Claude Code research.


From me: "can you extend pylint to do custom checks unique to your application"

# Extending Pylint with Custom Checks

Yes, absolutely! Pylint is designed to be extensible through **custom checker plugins**. You can write your own checkers to enforce project-specific coding standards.

## How It Works

You create a **checker class** that inherits from Pylint's base checkers and register it as a plugin.

## Basic Custom Checker

```python
# my_custom_checker.py
import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

class NoDirectPrintChecker(BaseChecker):
    """Disallow direct print() calls — enforce using logger instead."""

    __implements__ = IAstroidChecker

    name = "no-direct-print"

    # Unique message IDs (C = convention, W = warning, E = error, R = refactor)
    msgs = {
        "W9001": (
            "Direct print() call found. Use logger instead.",
            "no-direct-print",
            "All output should go through the logging module.",
        ),
    }

    # Optional: add command-line options
    options = (
        (
            "allow-print-in-tests",
            {
                "default": False,
                "type": "yn",
                "metavar": "<y or n>",
                "help": "Allow print() in test files.",
            },
        ),
    )

    def visit_call(self, node):
        """Called for every function call in the code."""
        if (
            isinstance(node.func, astroid.Name)
            and node.func.name == "print"
        ):
            self.add_message("no-direct-print", node=node)


def register(linter):
    """Required function to register the checker with pylint."""
    linter.register_checker(NoDirectPrintChecker(linter))
```

## More Complex Example — Domain-Specific Rules

```python
# django_checker.py
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

class DjangoModelChecker(BaseChecker):
    """Enforce project-specific Django conventions."""

    __implements__ = IAstroidChecker

    name = "django-model-conventions"

    msgs = {
        "E9010": (
            "Model %s is missing a __str__ method",
            "model-missing-str",
            "All Django models must implement __str__.",
        ),
        "W9011": (
            "Model %s is missing class Meta with ordering",
            "model-missing-ordering",
            "All models should define default ordering.",
        ),
        "E9012": (
            "Raw SQL detected in %s — use ORM instead",
            "no-raw-sql",
            "Direct SQL queries are prohibited.",
        ),
    }

    def visit_classdef(self, node):
        """Check Django model classes."""
        # Check if it inherits from models.Model
        if not self._is_django_model(node):
            return

        # Check for __str__
        method_names = [m.name for m in node.mymethods()]
        if "__str__" not in method_names:
            self.add_message("model-missing-str", node=node, args=(node.name,))

        # Check for Meta.ordering
        if not self._has_meta_ordering(node):
            self.add_message("model-missing-ordering", node=node, args=(node.name,))

    def visit_call(self, node):
        """Detect raw SQL usage."""
        if hasattr(node.func, "attrname") and node.func.attrname == "raw":
            self.add_message("no-raw-sql", node=node, args=(node.as_string(),))

    def _is_django_model(self, node):
        for ancestor in node.ancestors():
            if ancestor.name == "Model":
                return True
        return False

    def _has_meta_ordering(self, node):
        for child in node.body:
            if hasattr(child, "name") and child.name == "Meta":
                for attr in child.body:
                    if hasattr(attr, "targets"):
                        for target in attr.targets:
                            if hasattr(target, "name") and target.name == "ordering":
                                return True
        return False


def register(linter):
    linter.register_checker(DjangoModelChecker(linter))
```

## Using Your Plugin

### Method 1: Command line
```bash
pylint --load-plugins=my_custom_checker myproject/
```

### Method 2: In `pyproject.toml`
```toml
[tool.pylint.main]
load-plugins = [
    "my_custom_checker",
    "django_checker",
]
```

### Method 3: In `.pylintrc`
```ini
[MASTER]
load-plugins=my_custom_checker,django_checker
```

### Method 4: As a package (recommended for teams)
```
my_pylint_plugins/
├── __init__.py
├── print_checker.py
├── django_checker.py
└── security_checker.py
```

```python
# my_pylint_plugins/__init__.py
from my_pylint_plugins.print_checker import register as reg_print
from my_pylint_plugins.django_checker import register as reg_django

def register(linter):
    reg_print(linter)
    reg_django(linter)
```

## Available AST Visitor Methods

```python
class MyChecker(BaseChecker):
    # These are called automatically when pylint walks the AST:

    def visit_functiondef(self, node):    # function definitions
    def visit_classdef(self, node):       # class definitions
    def visit_call(self, node):           # function calls
    def visit_import(self, node):         # import statements
    def visit_importfrom(self, node):     # from ... import ...
    def visit_assign(self, node):         # assignments
    def visit_return(self, node):         # return statements
    def visit_raise(self, node):          # raise statements
    def visit_try(self, node):            # try/except blocks
    def visit_with(self, node):           # with statements
    def visit_global(self, node):         # global declarations
    def visit_attribute(self, node):      # attribute access (obj.attr)

    # "leave_" variants are called after processing children:
    def leave_functiondef(self, node):
    def leave_classdef(self, node):
```

## Testing Your Checker

```python
# test_checker.py
import pylint.testutils
from my_custom_checker import NoDirectPrintChecker

class TestNoDirectPrint(pylint.testutils.UnittestLinter):
    CHECKER_CLASS = NoDirectPrintChecker

    def test_print_detected(self):
        node = astroid.parse("""
            print("hello")  # should trigger warning
        """)
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="no-direct-print",
                line=2,
            )
        ):
            self.walk(node)
```

## Message ID Conventions

| Prefix | Category | Range |
|--------|----------|-------|
| `C` | Convention | `C9001-C9999` |
| `W` | Warning | `W9001-W9999` |
| `E` | Error | `E9001-E9999` |
| `R` | Refactor | `R9001-R9999` |

> Use the **9xxx** range for custom messages to avoid conflicts with built-in pylint messages.

This approach lets you enforce anything from **API usage patterns**, **security policies**, **naming conventions**, to **architecture rules** specific to your codebase.

From me: "For example, could you check that, under an "examples" directory, files with a main() function should not do `print()`?"

# Yes! Here's Exactly That Checker

```python
# examples_print_checker.py
import os
import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker


class ExamplesNoPrintChecker(BaseChecker):
    """In the examples/ directory, files with a main() function
    should use logging instead of print()."""

    __implements__ = IAstroidChecker

    name = "examples-no-print"

    msgs = {
        "W9001": (
            "print() used in examples/ file that has a main() function. "
            "Use logging instead.",
            "examples-no-print",
            "Example scripts with main() should demonstrate proper logging, "
            "not print().",
        ),
    }

    def visit_module(self, node):
        """Check if we're in an examples/ directory and if the module has main()."""
        filepath = node.file
        if filepath is None:
            return

        # Normalize path separators
        normalized = os.path.normpath(filepath)
        parts = normalized.split(os.sep)

        # Check if file lives under an "examples" directory
        self._in_examples = "examples" in parts

        # Check if the module defines a main() function
        self._has_main = any(
            isinstance(child, astroid.FunctionDef) and child.name == "main"
            for child in node.body
        )

    def visit_call(self, node):
        """Flag print() calls if both conditions are met."""
        if not self._in_examples or not self._has_main:
            return

        if isinstance(node.func, astroid.Name) and node.func.name == "print":
            self.add_message("examples-no-print", node=node)


def register(linter):
    linter.register_checker(ExamplesNoPrintChecker(linter))
```

## Let's See It in Action

### File: `examples/basic_usage.py` — ❌ Will trigger warnings
```python
import logging

def main():
    print("Starting...")          # ⚠ W9001
    result = do_something()
    print(f"Result: {result}")    # ⚠ W9001

def do_something():
    return 42

if __name__ == "__main__":
    main()
```

### File: `examples/basic_usage.py` — ✅ Clean version
```python
import logging

logger = logging.getLogger(__name__)

def main():
    logger.info("Starting...")
    result = do_something()
    logger.info("Result: %s", result)

def do_something():
    return 42

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

### File: `examples/constants.py` — ✅ No warning (no `main()`)
```python
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080
print("Module loaded")   # No warning — no main() in this file
```

### File: `src/core/engine.py` — ✅ No warning (not in `examples/`)
```python
def main():
    print("This is fine")  # Not under examples/, so no warning
```

## Run It

```bash
pylint --load-plugins=examples_print_checker examples/
```

### Sample output:
```
examples/basic_usage.py:4:4: W9001: print() used in examples/ file that has
    a main() function. Use logging instead. (examples-no-print)
examples/basic_usage.py:6:4: W9001: print() used in examples/ file that has
    a main() function. Use logging instead. (examples-no-print)
```

## Refinement: Handle Nested `print()` Calls Too

The basic version catches top-level `print()` calls, but what about `print()` inside `main()` or helper functions? It already works because `visit_call` is triggered for **every** call node in the AST regardless of nesting. But if you wanted to **only** flag `print()` inside `main()` specifically:

```python
def visit_functiondef(self, node):
    """Track when we enter main()."""
    if node.name == "main":
        self._inside_main = True

def leave_functiondef(self, node):
    """Track when we leave main()."""
    if node.name == "main":
        self._inside_main = False

def visit_call(self, node):
    if not self._in_examples or not self._inside_main:
        return

    if isinstance(node.func, astroid.Name) and node.func.name == "print":
        self.add_message("examples-no-print", node=node)
```

This shows the power of combining `visit_` and `leave_` hooks to track **scope context** as Pylint walks the AST.

From me: "can this idea exist in a CST such as libcst instead of an AST?"

# Yes! And LibCST Is Arguably Better For This

LibCST preserves formatting, comments, and whitespace — making it ideal for **autofixing** the violations too, not just detecting them.

## Detection Only (Like the Pylint Version)

```python
# examples_print_checker_cst.py
import os
import libcst as cst
from pathlib import Path


class ExamplesNoPrintChecker(cst.CSTVisitor):
    """Detect print() in examples/ files that define main()."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.in_examples = "examples" in Path(filepath).parts
        self.has_main = False
        self.inside_main = False
        self.violations: list[tuple[int, int, str]] = []

    # --- First pass concern: does main() exist? ---

    def visit_FunctionDef(self, node: cst.FunctionDef):
        if node.name.value == "main":
            self.has_main = True
            self.inside_main = True

    def leave_FunctionDef(self, node: cst.FunctionDef):
        if node.name.value == "main":
            self.inside_main = False

    def visit_Call(self, node: cst.Call):
        if not self.in_examples or not self.has_main:
            return

        # Match print(...)
        if isinstance(node.func, cst.Name) and node.func.value == "print":
            pos = self.get_metadata(
                cst.metadata.PositionProvider, node
            )
            self.violations.append((
                pos.start.line,
                pos.start.column,
                "print() used in examples/ file with main(). Use logging.",
            ))


def check_file(filepath: str) -> list[tuple[int, int, str]]:
    """Check a single file for violations."""
    source = Path(filepath).read_text()
    tree = cst.metadata.MetadataWrapper(cst.parse_module(source))
    checker = ExamplesNoPrintChecker(filepath)
    tree.visit(checker)
    return checker.violations


# --- CLI usage ---
if __name__ == "__main__":
    import sys

    for path in sys.argv[1:]:
        for line, col, msg in check_file(path):
            print(f"{path}:{line}:{col}: {msg}")
```

## But Here's Where CST Shines — Autofix!

```python
# examples_print_fixer.py
import libcst as cst
from pathlib import Path


class PrintToLoggingTransformer(cst.CSTTransformer):
    """Replace print() with logger.info() in examples/ files with main()."""

    METADATA_DEPENDENCIES = (cst.metadata.ParentNodeProvider,)

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.in_examples = "examples" in Path(filepath).parts
        self.has_main = False
        self.needs_logger_import = False

    def visit_FunctionDef(self, node: cst.FunctionDef):
        if node.name.value == "main":
            self.has_main = True

    def leave_Call(
        self, original: cst.Call, updated: cst.Call
    ) -> cst.BaseExpression:
        if not self.in_examples or not self.has_main:
            return updated

        if isinstance(updated.func, cst.Name) and updated.func.value == "print":
            self.needs_logger_import = True

            # Convert print args to logger.info format
            # print("msg", var) → logger.info("msg %s", var)
            args = list(updated.args)

            if len(args) == 1:
                # Simple case: print("hello") → logger.info("hello")
                return updated.with_changes(
                    func=cst.Attribute(
                        value=cst.Name("logger"),
                        attr=cst.Name("info"),
                    )
                )
            else:
                # Multi-arg: print("val:", x) → logger.info("val: %s", x)
                first_arg = args[0]
                rest_args = args[1:]

                # Build format string
                if isinstance(first_arg.value, (cst.SimpleString, cst.FormattedString)):
                    raw = first_arg.value.evaluated_value if isinstance(
                        first_arg.value, cst.SimpleString
                    ) else None

                    if raw is not None:
                        placeholders = " %s" * len(rest_args)
                        new_fmt = cst.Arg(
                            value=cst.SimpleString(f'"{raw}{placeholders}"')
                        )
                        new_args = [new_fmt] + rest_args
                        return updated.with_changes(
                            func=cst.Attribute(
                                value=cst.Name("logger"),
                                attr=cst.Name("info"),
                            ),
                            args=new_args,
                        )

                # Fallback: just swap function name
                return updated.with_changes(
                    func=cst.Attribute(
                        value=cst.Name("logger"),
                        attr=cst.Name("info"),
                    )
                )

        return updated

    def leave_Module(
        self, original: cst.Module, updated: cst.Module
    ) -> cst.Module:
        """Add logging import and logger definition if needed."""
        if not self.needs_logger_import:
            return updated

        # Build the import and logger lines
        import_line = cst.parse_statement("import logging\n")
        logger_line = cst.parse_statement(
            'logger = logging.getLogger(__name__)\n'
        )

        # Check if they already exist
        source = updated.code
        new_body = list(updated.body)

        if "import logging" not in source:
            new_body.insert(0, logger_line)
            new_body.insert(0, import_line)
        elif 'getLogger' not in source:
            # Find where to insert logger = ... (after imports)
            insert_idx = 0
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, (cst.SimpleStatementLine,)):
                    for item in stmt.body:
                        if isinstance(item, (cst.Import, cst.ImportFrom)):
                            insert_idx = i + 1
            new_body.insert(insert_idx, logger_line)

        return updated.with_changes(body=new_body)


def fix_file(filepath: str) -> str:
    """Transform a file and return the new source."""
    source = Path(filepath).read_text()
    tree = cst.parse_module(source)
    wrapper = cst.metadata.MetadataWrapper(tree)
    transformer = PrintToLoggingTransformer(filepath)
    new_tree = wrapper.visit(transformer)
    return new_tree.code


# --- Example usage ---
if __name__ == "__main__":
    import sys

    filepath = sys.argv[1]
    result = fix_file(filepath)

    if "--write" in sys.argv:
        Path(filepath).write_text(result)
        print(f"Fixed {filepath}")
    else:
        print(result)
```

## Demo

```bash
$ python examples_print_fixer.py examples/basic_usage.py
```

### Before:
```python
def main():
    print("Starting...")
    result = do_something()
    print(f"Result: {result}")
```

### After:
```python
import logging
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting...")
    result = do_something()
    logger.info(f"Result: {result}")
```

## AST vs CST — Key Differences Here

```
Feature               AST (Pylint)         CST (LibCST)
─────────────────────────────────────────────────────────
Detect violations     ✅ Yes               ✅ Yes
Preserve formatting   ❌ No                ✅ Yes
Preserve comments     ❌ No                ✅ Yes
Autofix code          ❌ Impractical       ✅ Natural
Round-trip fidelity   ❌ Lossy             ✅ Exact
Integration           Built-in to pylint   Standalone / custom
Complexity            Simpler              More verbose
```

## Two-Pass Approach (If You Need `has_main` Before Checking)

One subtlety: `visit_Call` might fire *before* `visit_FunctionDef` for `main()` if `print()` appears above `main()` in the file. A clean solution:

```python
class TwoPassChecker:
    """Pass 1: detect main(). Pass 2: flag print()."""

    def check(self, filepath: str):
        source = Path(filepath).read_text()
        tree = cst.parse_module(source)

        # Pass 1 — lightweight scan for main()
        has_main = any(
            isinstance(stmt, cst.FunctionDef) and stmt.name.value == "main"
            for stmt in tree.body
        )

        if not has_main:
            return []

        # Pass 2 — full violation detection
        wrapper = cst.metadata.MetadataWrapper(tree)
        checker = PrintViolationVisitor(filepath)
        wrapper.visit(checker)
        return checker.violations
```

The bottom line: **Pylint plugins are great for detection-only**, but **LibCST is the better choice when you also want to autofix**, since it can modify code while preserving every comment, blank line, and formatting choice.

## ACTIION: Monty!

This document researches "extensible linter" in pylint as an approach for doing custom "rules". The libcst research 
then looks at not just detecting, but correcting. Presumbably with the same custom-code, custom-rules approach.

Could Monty be used to write and run such custom rules?