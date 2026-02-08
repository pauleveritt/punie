"""Tests for session registration and tool caching.

Covers:
- SessionState frozen dataclass verification
- Tool discovery in new_session() (registration)
- Cached state usage in prompt() (no re-discovery)
- Lazy fallback for unknown session IDs
- Legacy agent compatibility
- FakeClient discovery call tracking
"""

import pytest

from punie.acp.schema import ClientCapabilities, FileSystemCapability, TextContentBlock
from punie.agent import PunieAgent, SessionState
from punie.agent.discovery import ToolCatalog
from punie.testing import FakeClient


def test_session_state_is_frozen():
    """SessionState is a frozen dataclass (immutable)."""
    from dataclasses import FrozenInstanceError
    from punie.agent.factory import create_pydantic_agent
    from punie.agent.toolset import create_toolset

    toolset = create_toolset()
    agent = create_pydantic_agent(model="test", toolset=toolset)

    state = SessionState(
        catalog=None,
        agent=agent,
        discovery_tier=3,
    )

    with pytest.raises(FrozenInstanceError):
        state.discovery_tier = 1  # type: ignore


def test_session_state_stores_fields():
    """SessionState stores catalog, agent, and discovery_tier."""
    from punie.agent.factory import create_pydantic_agent
    from punie.agent.toolset import create_toolset

    toolset = create_toolset()
    agent = create_pydantic_agent(model="test", toolset=toolset)
    catalog = ToolCatalog(tools=())

    state = SessionState(catalog=catalog, agent=agent, discovery_tier=1)

    assert state.catalog is catalog
    assert state.agent is agent
    assert state.discovery_tier == 1


@pytest.mark.asyncio
async def test_new_session_discovers_tools_once():
    """new_session() calls discover_tools() exactly once."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])

    assert len(fake.discover_tools_calls) == 1
    assert fake.discover_tools_calls[0] == response.session_id


@pytest.mark.asyncio
async def test_new_session_caches_session_state():
    """new_session() caches SessionState in _sessions dict."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    session_id = response.session_id

    assert session_id in agent._sessions
    state = agent._sessions[session_id]
    assert isinstance(state, SessionState)
    assert state.catalog is not None
    assert state.agent is not None


@pytest.mark.asyncio
async def test_new_session_records_discovery_tier():
    """new_session() records correct discovery_tier."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    state = agent._sessions[response.session_id]

    # Tier 1: catalog-based discovery
    assert state.discovery_tier == 1
    assert state.catalog is not None
    assert len(state.catalog.tools) == 1


@pytest.mark.asyncio
async def test_new_session_tier_2_fallback():
    """new_session() uses Tier 2 (capabilities) when no catalog."""
    fake = FakeClient(
        tool_catalog=[],  # Empty catalog triggers Tier 2
        capabilities=ClientCapabilities(fs=FileSystemCapability()),
    )
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(
        protocol_version=1,
        client_capabilities=ClientCapabilities(fs=FileSystemCapability()),
    )

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    state = agent._sessions[response.session_id]

    # Tier 2: capabilities fallback
    assert state.discovery_tier == 2
    assert state.catalog is None


@pytest.mark.asyncio
async def test_new_session_tier_3_fallback():
    """new_session() uses Tier 3 (default) when no catalog or capabilities."""
    fake = FakeClient(tool_catalog=[])  # Empty catalog, no capabilities
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    state = agent._sessions[response.session_id]

    # Tier 3: default toolset
    assert state.discovery_tier == 3
    assert state.catalog is None


@pytest.mark.asyncio
async def test_new_session_graceful_failure():
    """new_session() handles discovery failure gracefully."""

    class FailingClient(FakeClient):
        async def discover_tools(self, session_id: str, **kwargs):
            raise RuntimeError("Discovery failed")

    fake = FailingClient(capabilities=ClientCapabilities(fs=FileSystemCapability()))
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(
        protocol_version=1,
        client_capabilities=ClientCapabilities(fs=FileSystemCapability()),
    )

    # Should not raise, should fall back to Tier 2
    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    state = agent._sessions[response.session_id]

    assert state.discovery_tier == 2  # Fell back to capabilities


@pytest.mark.asyncio
async def test_prompt_uses_cached_agent():
    """prompt() uses cached agent from _sessions."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    session_id = response.session_id
    cached_agent = agent._sessions[session_id].agent

    # prompt() should use the cached agent
    await agent.prompt(
        prompt=[TextContentBlock(text="Hello", type="text")], session_id=session_id
    )

    # Verify same agent instance was used (check via _sessions)
    assert agent._sessions[session_id].agent is cached_agent


@pytest.mark.asyncio
async def test_prompt_does_not_re_discover():
    """prompt() does not call discover_tools() again after new_session()."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    session_id = response.session_id

    # One call from new_session()
    assert len(fake.discover_tools_calls) == 1

    # prompt() should NOT trigger another discovery call
    await agent.prompt(
        prompt=[TextContentBlock(text="Hello", type="text")], session_id=session_id
    )

    # Still only one call
    assert len(fake.discover_tools_calls) == 1


@pytest.mark.asyncio
async def test_prompt_multiple_calls_single_discovery():
    """Multiple prompt() calls use cached state, single discovery."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    session_id = response.session_id

    # Call prompt() multiple times
    for _ in range(3):
        await agent.prompt(
            prompt=[TextContentBlock(text="Hello", type="text")], session_id=session_id
        )

    # Still only one discovery call (from new_session)
    assert len(fake.discover_tools_calls) == 1


@pytest.mark.asyncio
async def test_prompt_lazy_fallback_unknown_session():
    """prompt() triggers lazy discovery for unknown session_id."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    # Call prompt() without calling new_session() first
    unknown_session_id = "unknown-session-123"
    await agent.prompt(
        prompt=[TextContentBlock(text="Hello", type="text")],
        session_id=unknown_session_id,
    )

    # Lazy fallback should have triggered discovery
    assert len(fake.discover_tools_calls) == 1
    assert fake.discover_tools_calls[0] == unknown_session_id


@pytest.mark.asyncio
async def test_prompt_lazy_fallback_caches_result():
    """Lazy fallback caches result for reuse."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    unknown_session_id = "unknown-session-123"

    # First call triggers lazy discovery
    await agent.prompt(
        prompt=[TextContentBlock(text="Hello", type="text")],
        session_id=unknown_session_id,
    )

    # Session state should be cached now
    assert unknown_session_id in agent._sessions

    # Second call should use cached state
    await agent.prompt(
        prompt=[TextContentBlock(text="Hello", type="text")],
        session_id=unknown_session_id,
    )

    # Still only one discovery call
    assert len(fake.discover_tools_calls) == 1


@pytest.mark.asyncio
async def test_legacy_agent_skips_registration():
    """Legacy agent mode skips registration in new_session()."""
    from punie.agent.factory import create_pydantic_agent
    from punie.agent.toolset import create_toolset

    toolset = create_toolset()
    legacy_agent = create_pydantic_agent(model="test", toolset=toolset)

    fake = FakeClient(tool_catalog=[{"name": "dummy", "kind": "read"}])
    agent = PunieAgent(model=legacy_agent)  # Pass agent instance
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])

    # No discovery should occur in legacy mode
    assert len(fake.discover_tools_calls) == 0
    # No session state cached
    assert response.session_id not in agent._sessions


@pytest.mark.asyncio
async def test_legacy_agent_still_works():
    """Legacy agent mode still works with prompt()."""
    from punie.agent.factory import create_pydantic_agent
    from punie.agent.toolset import create_toolset

    toolset = create_toolset()
    legacy_agent = create_pydantic_agent(model="test", toolset=toolset)

    fake = FakeClient()
    agent = PunieAgent(model=legacy_agent)
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    response = await agent.new_session(cwd="/tmp", mcp_servers=[])

    # prompt() should work with legacy agent
    await agent.prompt(
        prompt=[TextContentBlock(text="Hello", type="text")],
        session_id=response.session_id,
    )

    # Should have sent response
    assert len(fake.notifications) > 0


@pytest.mark.asyncio
async def test_fake_client_tracks_discover_calls():
    """FakeClient.discover_tools_calls tracks session_ids correctly."""
    tool_desc = {
        "name": "read_file",
        "kind": "read",
        "description": "Read file",
        "parameters": {"type": "object"},
    }
    fake = FakeClient(tool_catalog=[tool_desc])

    # Call discover_tools directly
    await fake.discover_tools(session_id="session-1")
    await fake.discover_tools(session_id="session-2")
    await fake.discover_tools(session_id="session-1")  # Repeat

    assert fake.discover_tools_calls == ["session-1", "session-2", "session-1"]
