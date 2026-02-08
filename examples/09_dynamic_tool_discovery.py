"""Example 09: Dynamic Tool Discovery

Demonstrates dynamic tool discovery via the three-tier fallback system.

This example shows:
- Creating ToolDescriptor and ToolCatalog
- Querying catalog (by_name, by_kind, by_category)
- Building Pydantic AI toolsets from catalogs
- Three-tier fallback: catalog → capabilities → default

Tier: 1 (Working)
"""

from punie.acp.schema import ClientCapabilities, FileSystemCapability
from punie.agent.discovery import ToolCatalog, ToolDescriptor
from punie.agent.toolset import (
    create_toolset,
    create_toolset_from_capabilities,
    create_toolset_from_catalog,
)


def main() -> None:
    """Demonstrate dynamic tool discovery and catalog queries."""

    # ============================================================
    # PART 1: Tool Discovery via Catalog (Tier 1)
    # ============================================================

    # IDE returns tool catalog via discover_tools()
    descriptors = [
        ToolDescriptor(
            name="read_file",
            kind="read",
            description="Read contents of a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            requires_permission=False,
            categories=("file", "io"),
        ),
        ToolDescriptor(
            name="write_file",
            kind="edit",
            description="Write contents to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
            requires_permission=True,
            categories=("file", "io"),
        ),
        ToolDescriptor(
            name="refactor_rename",
            kind="edit",
            description="Rename a symbol across the project",
            parameters={
                "type": "object",
                "properties": {
                    "old_name": {"type": "string"},
                    "new_name": {"type": "string"},
                },
            },
            requires_permission=True,
            categories=("refactoring", "ide"),
        ),
    ]

    catalog = ToolCatalog(tools=tuple(descriptors))

    print("=== Tool Discovery (Tier 1) ===")
    print(f"Total tools in catalog: {len(catalog.tools)}")

    # Query by name
    read_tool = catalog.by_name("read_file")
    if read_tool:
        print(f"\nFound by name: {read_tool.name}")
        print(f"  Kind: {read_tool.kind}")
        print(f"  Description: {read_tool.description}")
        print(f"  Permission required: {read_tool.requires_permission}")

    # Query by kind
    edit_tools = catalog.by_kind("edit")
    print(f"\nTools with kind='edit': {len(edit_tools)}")
    for tool in edit_tools:
        print(f"  - {tool.name}: {tool.description}")

    # Query by category
    file_tools = catalog.by_category("file")
    print(f"\nTools with category='file': {len(file_tools)}")
    for tool in file_tools:
        print(f"  - {tool.name}")

    refactoring_tools = catalog.by_category("refactoring")
    print(f"\nTools with category='refactoring': {len(refactoring_tools)}")
    for tool in refactoring_tools:
        print(f"  - {tool.name}")

    # Build Pydantic AI toolset from catalog
    toolset = create_toolset_from_catalog(catalog)
    print(f"\nBuilt toolset with {len(toolset.tools)} tools from catalog")
    for tool_name in toolset.tools:
        print(f"  - {tool_name}")

    # ============================================================
    # PART 2: Capability-Based Fallback (Tier 2)
    # ============================================================

    print("\n=== Capability-Based Fallback (Tier 2) ===")

    # When discover_tools() is unavailable, use client capabilities
    caps = ClientCapabilities(
        fs=FileSystemCapability(read_text_file=True, write_text_file=True),
        terminal=True,
    )

    toolset_from_caps = create_toolset_from_capabilities(caps)
    print(f"Built toolset with {len(toolset_from_caps.tools)} tools from capabilities")
    for tool_name in toolset_from_caps.tools:
        print(f"  - {tool_name}")

    # ============================================================
    # PART 3: Default Fallback (Tier 3)
    # ============================================================

    print("\n=== Default Fallback (Tier 3) ===")

    # When no discovery and no capabilities, use all 7 static tools
    default_toolset = create_toolset()
    print(f"Built default toolset with {len(default_toolset.tools)} tools")
    for tool_name in default_toolset.tools:
        print(f"  - {tool_name}")

    # ============================================================
    # PART 4: Unknown Tool Handling (Generic Bridge)
    # ============================================================

    print("\n=== Unknown Tool Handling ===")

    # When IDE provides a tool not in the known set, generic bridge is created
    unknown_tool = ToolDescriptor(
        name="ide_debug_breakpoint",
        kind="execute",
        description="Set a debugger breakpoint",
        parameters={
            "type": "object",
            "properties": {
                "file": {"type": "string"},
                "line": {"type": "number"},
            },
        },
    )
    unknown_catalog = ToolCatalog(tools=(unknown_tool,))
    unknown_toolset = create_toolset_from_catalog(unknown_catalog)

    tool = unknown_toolset.tools["ide_debug_breakpoint"]
    print(f"Unknown tool creates generic bridge: {tool.name}")
    print(f"  Description: {tool.description}")

    print("\n✓ Dynamic tool discovery demonstrated")


if __name__ == "__main__":
    main()
