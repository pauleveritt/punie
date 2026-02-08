"""Example 09: Dynamic Tool Discovery (Aspirational)

Demonstrates dynamic tool discovery pattern for Phase 4.

**STATUS: ASPIRATIONAL** — This example shows the intended discovery pattern.
The ToolKind enumeration and grouping works today. The discovery protocol is
documented in comments as future functionality.

This example shows:
- Current: Enumerating all ToolKind values (works today)
- Current: Grouping tools by category (works today)
- Future: Runtime discovery protocol (Phase 4)
- Future: IDE advertises available tools dynamically
- Future: Agent queries tool catalog at session start

For implementation reference, see:
- acp.schema.ToolKind enum definition

Tier: 3 (Aspirational)
"""

from punie.acp import start_tool_call
from punie.acp.schema import ToolCallLocation


def main() -> None:
    """Demonstrate current tool enumeration and future discovery pattern."""

    # ============================================================
    # PART 1: What works today — Tool enumeration and grouping
    # ============================================================

    # Tool kinds as defined in ACP schema (lowercase)
    ide_tools = [
        "read",
        "edit",
        "delete",
        "move",
        "search",
        "execute",
    ]

    # Agent tools (AI-specific operations)
    agent_tools = [
        "think",
    ]

    # Meta tools (protocol operations)
    meta_tools = [
        "fetch",
        "switch_mode",
        "other",
    ]

    all_tools = ide_tools + agent_tools + meta_tools

    # Demonstrate constructing a tool call for each category
    for idx, tool_kind in enumerate(ide_tools[:3]):  # Sample first 3 IDE tools
        tool_call = start_tool_call(
            f"call-{idx}",
            f"Using {tool_kind}",
            kind=tool_kind,  # ty: ignore[invalid-argument-type]  # tool_kind is string from literal list
            status="in_progress",
            locations=[ToolCallLocation(path="/example/file.py")],
            raw_input=f'{{"kind": "{tool_kind}"}}',
        )
        assert tool_call.kind == tool_kind

    print(
        f"✓ Current functionality: {len(all_tools)} tool kinds enumerated and grouped"
    )
    print(f"  - IDE tools: {len(ide_tools)}")
    print(f"  - Agent tools: {len(agent_tools)}")
    print(f"  - Meta tools: {len(meta_tools)}")

    # ============================================================
    # PART 2: Future pattern — Dynamic tool discovery (Phase 4)
    # ============================================================

    # The intended pattern (not yet implemented):
    #
    # # At session initialization, agent queries available tools
    # tool_catalog = await acp_client.discover_tools(session_id)
    #
    # # tool_catalog structure:
    # # {
    # #   "ide_tools": [
    # #     {
    # #       "kind": "Read",
    # #       "schema": {...},  # JSON schema for parameters
    # #       "description": "Read file contents",
    # #       "categories": ["file", "io"]
    # #     },
    # #     {
    # #       "kind": "Edit",
    # #       "schema": {...},
    # #       "description": "Edit file with string replacement",
    # #       "categories": ["file", "io", "write"]
    # #     },
    # #     ...
    # #   ],
    # #   "agent_tools": [...],
    # #   "meta_tools": [...]
    # # }
    #
    # # Agent can now:
    # # 1. Query available tools dynamically
    # # 2. Filter by category ("show me all file tools")
    # # 3. Discover tool schemas without hardcoding
    # # 4. Adapt to IDE extensions adding new tools
    #
    # # Example: Find all tools that can modify files
    # write_tools = [
    #     tool for tool in tool_catalog["ide_tools"]
    #     if "write" in tool["categories"]
    # ]
    #
    # # Example: Get schema for Edit tool to construct call correctly
    # edit_schema = next(
    #     tool["schema"] for tool in tool_catalog["ide_tools"]
    #     if tool["kind"] == "Edit"
    # )
    #
    # Benefits:
    # - Tools not hardcoded in agent
    # - IDE can extend tool catalog via plugins
    # - Agent adapts to available tools automatically
    # - Schema-driven tool call construction
    # - Runtime capability negotiation

    print("✓ Future pattern: Dynamic tool discovery protocol documented")


if __name__ == "__main__":
    main()
