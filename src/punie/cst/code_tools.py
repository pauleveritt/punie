"""General-purpose LibCST code analysis and transformation tools.

Provides three tools usable on any Python project:
- cst_find_pattern: find nodes matching a pattern with line numbers
- cst_rename: rename a symbol across a file
- cst_add_import: add an import statement (idempotent)
"""

from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst.metadata import MetadataWrapper, PositionProvider

from punie.agent.typed_tools import CstAddImportResult, CstFindResult, CstMatch, CstRenameResult


def _pattern_to_matcher(pattern: str) -> object:
    """Convert a pattern string to a LibCST matcher.

    Supported patterns:
    - Node type names: "FunctionDef", "ClassDef", "Call", "Decorator",
      "Import", "ImportFrom", "Name", "Attribute"
    - Qualified: "call:name" (calls to a specific function)
    - Qualified: "decorator:name" (uses of a specific decorator)
    - Qualified: "import:name" (imports of a specific module/name)

    Args:
        pattern: Pattern string

    Returns:
        LibCST matcher object

    Raises:
        ValueError: If pattern is not recognized
    """
    if pattern.startswith("call:"):
        func_name = pattern[5:]
        return m.Call(func=m.Name(func_name))
    elif pattern.startswith("decorator:"):
        dec_name = pattern[10:]
        return m.Decorator(decorator=m.Name(dec_name))
    elif pattern.startswith("import:"):
        mod_name = pattern[7:]
        return m.ImportFrom(module=m.Attribute(attr=m.Name(mod_name))) | m.ImportFrom(
            module=m.Name(mod_name)
        )
    elif pattern == "FunctionDef":
        return m.FunctionDef()
    elif pattern == "ClassDef":
        return m.ClassDef()
    elif pattern == "Call":
        return m.Call()
    elif pattern == "Decorator":
        return m.Decorator()
    elif pattern == "Import":
        return m.Import()
    elif pattern == "ImportFrom":
        return m.ImportFrom()
    elif pattern == "Name":
        return m.Name()
    elif pattern == "Attribute":
        return m.Attribute()
    else:
        raise ValueError(f"Unknown pattern: {pattern!r}. Use 'FunctionDef', 'ClassDef', 'Call', 'Decorator', 'ImportFrom', 'call:name', 'decorator:name', 'import:name'")


def cst_find_pattern(file_path: str, pattern: str) -> CstFindResult:
    """Find all nodes matching a pattern in a Python file.

    Uses LibCST to parse the file and find nodes matching the given
    pattern, returning accurate line numbers via PositionProvider.

    Args:
        file_path: Path to the Python file to analyze
        pattern: Pattern to search for. Supported patterns:
            - "FunctionDef" — all function definitions
            - "ClassDef" — all class definitions
            - "Call" — all function calls
            - "Decorator" — all decorators
            - "ImportFrom" — all from ... import ... statements
            - "call:name" — calls to function named "name"
            - "decorator:name" — uses of decorator named "name"
            - "import:name" — imports from module named "name"

    Returns:
        CstFindResult with matches list (line, column, code_snippet, node_type)
    """
    try:
        with open(file_path) as f:
            source = f.read()
        module = cst.parse_module(source)
    except Exception as e:
        return CstFindResult(
            success=False, match_count=0, matches=[], parse_error=str(e)
        )

    try:
        matcher = _pattern_to_matcher(pattern)
    except ValueError as e:
        return CstFindResult(
            success=False, match_count=0, matches=[], parse_error=str(e)
        )

    try:
        wrapper = MetadataWrapper(module)
        positions = wrapper.resolve(PositionProvider)
        matches = m.findall(wrapper.module, matcher)

        result_matches = []
        for node in matches:
            pos = positions.get(node)
            line = pos.start.line if pos else 0
            col = pos.start.column if pos else 0
            snippet = wrapper.module.code_for_node(node)
            # Strip leading whitespace and get first meaningful line
            lines = [ln for ln in snippet.split("\n") if ln.strip()]
            first_line = lines[0].strip() if lines else ""
            if len(first_line) > 120:
                first_line = first_line[:117] + "..."
            result_matches.append(
                CstMatch(
                    line=line,
                    column=col,
                    code_snippet=first_line,
                    node_type=type(node).__name__,
                )
            )

        return CstFindResult(
            success=True,
            match_count=len(result_matches),
            matches=result_matches,
        )
    except Exception as e:
        return CstFindResult(
            success=False, match_count=0, matches=[], parse_error=str(e)
        )


class _RenameTransformer(cst.CSTTransformer):
    """CSTTransformer that renames all occurrences of a Name node."""

    def __init__(self, old_name: str, new_name: str) -> None:
        super().__init__()
        self.old_name = old_name
        self.new_name = new_name
        self.rename_count = 0

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.Name:
        if updated_node.value == self.old_name:
            self.rename_count += 1
            return updated_node.with_changes(value=self.new_name)
        return updated_node


def cst_rename(file_path: str, old_name: str, new_name: str) -> CstRenameResult:
    """Rename all occurrences of a symbol in a Python file.

    Uses a CSTTransformer to rename all Name nodes matching old_name
    to new_name. Preserves all whitespace and formatting.

    Args:
        file_path: Path to the Python file to modify
        old_name: Symbol name to rename
        new_name: New symbol name

    Returns:
        CstRenameResult with rename_count and modified_source
    """
    try:
        with open(file_path) as f:
            source = f.read()
        module = cst.parse_module(source)
    except Exception as e:
        return CstRenameResult(
            success=False, rename_count=0, parse_error=str(e)
        )

    try:
        transformer = _RenameTransformer(old_name, new_name)
        new_module = module.visit(transformer)
        return CstRenameResult(
            success=True,
            rename_count=transformer.rename_count,
            modified_source=new_module.code,
        )
    except Exception as e:
        return CstRenameResult(
            success=False, rename_count=0, parse_error=str(e)
        )


def _parse_import_string(import_stmt: str) -> tuple[str, str | None]:
    """Parse an import statement string into (module, object) tuple.

    Args:
        import_stmt: Import statement like "from typing import Optional"
            or "import os"

    Returns:
        (module_name, obj_name) where obj_name is None for bare imports

    Raises:
        ValueError: If the import statement format is not recognized
    """
    stmt = import_stmt.strip()
    if stmt.startswith("from "):
        parts = stmt.split(" import ", maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"Invalid from-import: {import_stmt!r}")
        module_name = parts[0][5:].strip()
        obj_name = parts[1].strip()
        return module_name, obj_name
    elif stmt.startswith("import "):
        module_name = stmt[7:].strip()
        return module_name, None
    else:
        raise ValueError(
            f"Import must start with 'from' or 'import': {import_stmt!r}"
        )


def cst_add_import(file_path: str, import_stmt: str) -> CstAddImportResult:
    """Add an import statement to a Python file (idempotent).

    Uses AddImportsVisitor to add the import only if not already present.
    Preserves all existing formatting.

    Args:
        file_path: Path to the Python file to modify
        import_stmt: Import statement to add, e.g.:
            - "from typing import Optional"
            - "from svcs_di import Inject"
            - "import os"

    Returns:
        CstAddImportResult with import_added flag and modified_source
    """
    try:
        with open(file_path) as f:
            source = f.read()
        module = cst.parse_module(source)
    except Exception as e:
        return CstAddImportResult(
            success=False, import_added=False, parse_error=str(e)
        )

    try:
        from libcst.codemod import CodemodContext
        from libcst.codemod.visitors import AddImportsVisitor

        module_name, obj_name = _parse_import_string(import_stmt)
        context = CodemodContext()
        if obj_name is None:
            AddImportsVisitor.add_needed_import(context, module_name)
        else:
            # Task 8: handle multi-name ("Optional, List") and aliases ("Optional as Opt")
            for name_part in (n.strip() for n in obj_name.split(",")):
                if " as " in name_part:
                    orig, alias = (p.strip() for p in name_part.split(" as ", 1))
                    AddImportsVisitor.add_needed_import(context, module_name, orig, alias)
                else:
                    AddImportsVisitor.add_needed_import(context, module_name, name_part)

        wrapper = MetadataWrapper(module)
        new_module = wrapper.visit(AddImportsVisitor(context))
        new_source = new_module.code
        import_added = new_source != source
        return CstAddImportResult(
            success=True,
            import_added=import_added,
            modified_source=new_source,
        )
    except Exception as e:
        return CstAddImportResult(
            success=False, import_added=False, parse_error=str(e)
        )
