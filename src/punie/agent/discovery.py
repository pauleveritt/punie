"""Dynamic tool discovery types for the Punie agent.

This module defines the schema types for discovering IDE-provided tools at runtime.
The catalog is built from the IDE's `discover_tools()` response and used to construct
session-specific toolsets.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDescriptor:
    """Descriptor for a single tool available from the IDE.

    This is an immutable value object representing a tool's metadata and parameter schema.
    Tools can be known (read_file, write_file, etc.) or IDE-provided (refactor_rename, etc.).

    >>> descriptor = ToolDescriptor(
    ...     name="read_file",
    ...     kind="read",
    ...     description="Read contents of a file",
    ...     parameters={"type": "object", "properties": {"path": {"type": "string"}}}
    ... )
    >>> descriptor.name
    'read_file'
    >>> descriptor.requires_permission
    False
    """

    name: str
    """Unique tool identifier (e.g. 'read_file', 'refactor_rename')."""

    kind: str
    """Tool kind from ToolKind Literal: 'read', 'edit', 'execute', etc."""

    description: str
    """Human-readable description shown to LLM."""

    parameters: dict[str, Any]
    """JSON Schema describing tool parameters."""

    requires_permission: bool = False
    """Whether this tool requires user permission before execution."""

    categories: tuple[str, ...] = ()
    """Tool categories for filtering (e.g. ('file', 'io'), ('refactoring',))."""


@dataclass(frozen=True)
class ToolCatalog:
    """Immutable catalog of available tools.

    Built from the IDE's `discover_tools()` response. Provides efficient lookup
    by name, kind, and category. Construct once, query many times.

    >>> descriptor = ToolDescriptor(
    ...     name="read_file",
    ...     kind="read",
    ...     description="Read file",
    ...     parameters={},
    ...     categories=("file", "io")
    ... )
    >>> catalog = ToolCatalog(tools=(descriptor,))
    >>> catalog.by_name("read_file").name
    'read_file'
    >>> len(catalog.by_category("io"))
    1
    """

    tools: tuple[ToolDescriptor, ...]
    """Immutable sequence of available tool descriptors."""

    def by_name(self, name: str) -> ToolDescriptor | None:
        """Look up a tool descriptor by name.

        >>> descriptor = ToolDescriptor(
        ...     name="read_file", kind="read", description="Read", parameters={}
        ... )
        >>> catalog = ToolCatalog(tools=(descriptor,))
        >>> catalog.by_name("read_file").name
        'read_file'
        >>> catalog.by_name("unknown") is None
        True
        """
        return next((t for t in self.tools if t.name == name), None)

    def by_kind(self, kind: str) -> tuple[ToolDescriptor, ...]:
        """Filter tools by kind (e.g. 'read', 'edit', 'execute').

        >>> read_desc = ToolDescriptor(
        ...     name="read_file", kind="read", description="Read", parameters={}
        ... )
        >>> edit_desc = ToolDescriptor(
        ...     name="write_file", kind="edit", description="Write", parameters={}
        ... )
        >>> catalog = ToolCatalog(tools=(read_desc, edit_desc))
        >>> len(catalog.by_kind("read"))
        1
        >>> len(catalog.by_kind("edit"))
        1
        >>> len(catalog.by_kind("execute"))
        0
        """
        return tuple(t for t in self.tools if t.kind == kind)

    def by_category(self, category: str) -> tuple[ToolDescriptor, ...]:
        """Filter tools by category (e.g. 'file', 'refactoring').

        >>> file_desc = ToolDescriptor(
        ...     name="read_file", kind="read", description="Read",
        ...     parameters={}, categories=("file", "io")
        ... )
        >>> refactor_desc = ToolDescriptor(
        ...     name="rename", kind="edit", description="Rename",
        ...     parameters={}, categories=("refactoring",)
        ... )
        >>> catalog = ToolCatalog(tools=(file_desc, refactor_desc))
        >>> len(catalog.by_category("file"))
        1
        >>> len(catalog.by_category("refactoring"))
        1
        >>> len(catalog.by_category("io"))
        1
        """
        return tuple(t for t in self.tools if category in t.categories)


def parse_tool_catalog(data: dict[str, Any]) -> ToolCatalog:
    """Parse a tool catalog from IDE's discover_tools() response.

    >>> data = {
    ...     "tools": [
    ...         {
    ...             "name": "read_file",
    ...             "kind": "read",
    ...             "description": "Read file",
    ...             "parameters": {"type": "object"},
    ...             "requires_permission": False,
    ...             "categories": ["file", "io"]
    ...         }
    ...     ]
    ... }
    >>> catalog = parse_tool_catalog(data)
    >>> len(catalog.tools)
    1
    >>> catalog.tools[0].name
    'read_file'
    """
    tools_data = data.get("tools", [])
    descriptors = tuple(
        ToolDescriptor(
            name=t["name"],
            kind=t["kind"],
            description=t["description"],
            parameters=t["parameters"],
            requires_permission=t.get("requires_permission", False),
            categories=tuple(t.get("categories", [])),
        )
        for t in tools_data
    )
    return ToolCatalog(tools=descriptors)
