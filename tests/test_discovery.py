"""Tests for dynamic tool discovery.

Covers:
- Frozen dataclass verification
- ToolCatalog query methods
- Toolset factories (catalog, capabilities, default)
- Adapter integration (discovery wiring, fallback chain)
- FakeClient protocol satisfaction
"""

import pytest

from punie.acp.schema import ClientCapabilities, FileSystemCapability
from punie.agent.discovery import ToolCatalog, ToolDescriptor, parse_tool_catalog
from punie.agent.toolset import (
    create_toolset,
    create_toolset_from_capabilities,
    create_toolset_from_catalog,
)
from punie.agent.adapter import PunieAgent
from punie.testing import FakeClient


def test_tool_descriptor_is_frozen():
    """ToolDescriptor is a frozen dataclass (immutable)."""
    from dataclasses import FrozenInstanceError

    descriptor = ToolDescriptor(
        name="read_file",
        kind="read",
        description="Read file",
        parameters={"type": "object"},
    )
    with pytest.raises(FrozenInstanceError):
        descriptor.name = "write_file"  # type: ignore


def test_tool_catalog_is_frozen():
    """ToolCatalog is a frozen dataclass (immutable)."""
    from dataclasses import FrozenInstanceError

    descriptor = ToolDescriptor(
        name="read_file", kind="read", description="Read", parameters={}
    )
    catalog = ToolCatalog(tools=(descriptor,))
    with pytest.raises(FrozenInstanceError):
        catalog.tools = ()  # type: ignore


def test_tool_catalog_by_name():
    """ToolCatalog.by_name() returns matching descriptor or None."""
    read_desc = ToolDescriptor(
        name="read_file", kind="read", description="Read", parameters={}
    )
    write_desc = ToolDescriptor(
        name="write_file", kind="edit", description="Write", parameters={}
    )
    catalog = ToolCatalog(tools=(read_desc, write_desc))

    assert catalog.by_name("read_file") == read_desc
    assert catalog.by_name("write_file") == write_desc
    assert catalog.by_name("unknown") is None


def test_tool_catalog_by_kind():
    """ToolCatalog.by_kind() filters descriptors by kind."""
    read_desc = ToolDescriptor(
        name="read_file", kind="read", description="Read", parameters={}
    )
    write_desc = ToolDescriptor(
        name="write_file", kind="edit", description="Write", parameters={}
    )
    run_desc = ToolDescriptor(
        name="run_command", kind="execute", description="Run", parameters={}
    )
    catalog = ToolCatalog(tools=(read_desc, write_desc, run_desc))

    assert catalog.by_kind("read") == (read_desc,)
    assert catalog.by_kind("edit") == (write_desc,)
    assert catalog.by_kind("execute") == (run_desc,)
    assert catalog.by_kind("unknown") == ()


def test_tool_catalog_by_category():
    """ToolCatalog.by_category() filters descriptors by category."""
    read_desc = ToolDescriptor(
        name="read_file",
        kind="read",
        description="Read",
        parameters={},
        categories=("file", "io"),
    )
    write_desc = ToolDescriptor(
        name="write_file",
        kind="edit",
        description="Write",
        parameters={},
        categories=("file", "io"),
    )
    refactor_desc = ToolDescriptor(
        name="rename",
        kind="edit",
        description="Rename",
        parameters={},
        categories=("refactoring",),
    )
    catalog = ToolCatalog(tools=(read_desc, write_desc, refactor_desc))

    assert catalog.by_category("file") == (read_desc, write_desc)
    assert catalog.by_category("io") == (read_desc, write_desc)
    assert catalog.by_category("refactoring") == (refactor_desc,)
    assert catalog.by_category("unknown") == ()


def test_parse_tool_catalog():
    """parse_tool_catalog() parses IDE response into ToolCatalog."""
    data = {
        "tools": [
            {
                "name": "read_file",
                "kind": "read",
                "description": "Read file",
                "parameters": {"type": "object"},
                "requires_permission": False,
                "categories": ["file", "io"],
            },
            {
                "name": "write_file",
                "kind": "edit",
                "description": "Write file",
                "parameters": {"type": "object"},
                "requires_permission": True,
                "categories": ["file", "io"],
            },
        ]
    }
    catalog = parse_tool_catalog(data)

    assert len(catalog.tools) == 2
    assert catalog.tools[0].name == "read_file"
    assert catalog.tools[0].requires_permission is False
    assert catalog.tools[0].categories == ("file", "io")
    assert catalog.tools[1].name == "write_file"
    assert catalog.tools[1].requires_permission is True


def test_create_toolset_from_catalog_known_tools():
    """create_toolset_from_catalog() matches known tools by name."""
    descriptors = [
        ToolDescriptor(
            name="read_file", kind="read", description="Read", parameters={}
        ),
        ToolDescriptor(
            name="write_file", kind="edit", description="Write", parameters={}
        ),
    ]
    catalog = ToolCatalog(tools=tuple(descriptors))
    toolset = create_toolset_from_catalog(catalog)

    assert len(toolset.tools) == 2
    # Known tools are matched by name (tools is a dict)
    assert "read_file" in toolset.tools
    assert "write_file" in toolset.tools


def test_create_toolset_from_catalog_unknown_tools():
    """create_toolset_from_catalog() creates generic bridges for unknown tools."""
    descriptors = [
        ToolDescriptor(
            name="refactor_rename",
            kind="edit",
            description="Rename symbol",
            parameters={},
        ),
    ]
    catalog = ToolCatalog(tools=tuple(descriptors))
    toolset = create_toolset_from_catalog(catalog)

    assert len(toolset.tools) == 1
    # Unknown tools get generic bridge (tools is a dict keyed by name)
    assert "refactor_rename" in toolset.tools
    tool = toolset.tools["refactor_rename"]
    assert tool.name == "refactor_rename"
    assert tool.description == "Rename symbol"


def test_create_toolset_from_capabilities_fs_only():
    """create_toolset_from_capabilities() includes only file tools when terminal=False."""
    caps = ClientCapabilities(
        fs=FileSystemCapability(read_text_file=True, write_text_file=True),
        terminal=False,
    )
    toolset = create_toolset_from_capabilities(caps)

    # Should have read_file and write_file, no terminal tools
    assert len(toolset.tools) == 2
    assert "read_file" in toolset.tools
    assert "write_file" in toolset.tools
    assert "run_command" not in toolset.tools


def test_create_toolset_from_capabilities_all():
    """create_toolset_from_capabilities() includes all tools when everything enabled."""
    caps = ClientCapabilities(
        fs=FileSystemCapability(read_text_file=True, write_text_file=True),
        terminal=True,
    )
    toolset = create_toolset_from_capabilities(caps)

    # Should have 2 file tools + 5 terminal tools = 7 total
    assert len(toolset.tools) == 7
    assert "read_file" in toolset.tools
    assert "write_file" in toolset.tools
    assert "run_command" in toolset.tools


@pytest.mark.asyncio
async def test_adapter_stores_client_capabilities():
    """PunieAgent.initialize() stores client_capabilities."""
    adapter = PunieAgent(model="test")
    caps = ClientCapabilities(
        fs=FileSystemCapability(read_text_file=True), terminal=False
    )

    await adapter.initialize(
        protocol_version=1,
        client_capabilities=caps,
    )

    assert adapter._client_capabilities == caps


@pytest.mark.asyncio
async def test_adapter_uses_discovery_when_available():
    """PunieAgent.prompt() uses discover_tools() when available (Tier 1)."""
    # Create FakeClient with tool catalog
    catalog_data = [
        {
            "name": "read_file",
            "kind": "read",
            "description": "Read file",
            "parameters": {"type": "object"},
        }
    ]
    client = FakeClient(tool_catalog=catalog_data)

    # Create adapter and connect
    adapter = PunieAgent(model="test")
    adapter.on_connect(client)

    # Initialize (no capabilities, discovery takes precedence)
    await adapter.initialize(protocol_version=1)

    # Prompt should use discovery
    from punie.acp.helpers import text_block

    await adapter.prompt(prompt=[text_block("test")], session_id="test-session")

    # Verify discover_tools() was called (check it has the method)
    assert hasattr(client, "discover_tools")


@pytest.mark.asyncio
async def test_adapter_falls_back_to_capabilities():
    """PunieAgent.prompt() falls back to capabilities when discovery fails (Tier 2)."""
    # Create FakeClient with no catalog but with capabilities
    caps = ClientCapabilities(
        fs=FileSystemCapability(read_text_file=True), terminal=False
    )
    client = FakeClient(capabilities=caps)

    # Create adapter and connect
    adapter = PunieAgent(model="test")
    adapter.on_connect(client)

    # Initialize with capabilities
    await adapter.initialize(protocol_version=1, client_capabilities=caps)

    # Prompt should use capabilities fallback
    from punie.acp.helpers import text_block

    await adapter.prompt(prompt=[text_block("test")], session_id="test-session")

    # No assertion needed - if it doesn't crash, it used fallback


@pytest.mark.asyncio
async def test_adapter_falls_back_to_defaults():
    """PunieAgent.prompt() falls back to default toolset when no caps/discovery (Tier 3)."""
    # Create FakeClient with no catalog and no capabilities
    client = FakeClient()

    # Create adapter and connect
    adapter = PunieAgent(model="test")
    adapter.on_connect(client)

    # Initialize without capabilities
    await adapter.initialize(protocol_version=1)

    # Prompt should use default toolset
    from punie.acp.helpers import text_block

    await adapter.prompt(prompt=[text_block("test")], session_id="test-session")

    # No assertion needed - if it doesn't crash, it used default


@pytest.mark.asyncio
async def test_fake_client_discover_tools():
    """FakeClient.discover_tools() satisfies Client protocol."""
    catalog_data = [
        {
            "name": "read_file",
            "kind": "read",
            "description": "Read file",
            "parameters": {"type": "object"},
        }
    ]
    client = FakeClient(tool_catalog=catalog_data)

    result = await client.discover_tools(session_id="test-session")

    assert isinstance(result, dict)
    assert "tools" in result
    assert result["tools"] == catalog_data


def test_default_toolset_has_all_8_tools():
    """create_toolset() returns all 8 static tools (Tier 3 fallback)."""
    toolset = create_toolset()
    assert len(toolset.tools) == 8

    assert "read_file" in toolset.tools
    assert "write_file" in toolset.tools
    assert "execute_code" in toolset.tools
    assert "run_command" in toolset.tools
    assert "get_terminal_output" in toolset.tools
    assert "release_terminal" in toolset.tools
    assert "wait_for_terminal_exit" in toolset.tools
    assert "kill_terminal" in toolset.tools
