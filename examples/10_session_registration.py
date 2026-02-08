"""Example 10: Session Registration

Demonstrates session-scoped tool registration and caching.

This example shows:
- Tools discovered once in new_session()
- SessionState caching for the session lifetime
- Multiple prompt() calls reuse cached agent
- Lazy fallback for sessions created without new_session()

Tier: 1 (Working)
"""

from punie.acp.schema import ClientCapabilities, FileSystemCapability, TextContentBlock
from punie.agent import PunieAgent, SessionState
from punie.testing import FakeClient


async def main() -> None:
    """Demonstrate session registration and tool caching."""

    # ============================================================
    # PART 1: Session Registration in new_session()
    # ============================================================

    print("=== Session Registration ===")

    # Create agent with tool catalog
    tool_catalog = [
        {
            "name": "read_file",
            "kind": "read",
            "description": "Read file contents",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
        },
        {
            "name": "write_file",
            "kind": "edit",
            "description": "Write file contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        },
    ]

    fake = FakeClient(tool_catalog=tool_catalog)
    agent = PunieAgent(model="test")
    agent.on_connect(fake)
    await agent.initialize(protocol_version=1)

    # new_session() discovers tools and caches SessionState
    response = await agent.new_session(cwd="/tmp", mcp_servers=[])
    session_id = response.session_id

    print(f"Created session: {session_id}")
    print(f"Discovery calls during new_session(): {len(fake.discover_tools_calls)}")

    # Verify SessionState was cached
    if session_id in agent._sessions:
        state: SessionState = agent._sessions[session_id]
        print(f"\nSessionState cached:")
        print(f"  Discovery tier: {state.discovery_tier}")
        print(f"  Catalog tools: {len(state.catalog.tools) if state.catalog else 0}")
        print(f"  Agent cached: {state.agent is not None}")

    # ============================================================
    # PART 2: Multiple prompt() calls use cached state
    # ============================================================

    print("\n=== Cached State Reuse ===")

    initial_discovery_calls = len(fake.discover_tools_calls)

    # Call prompt() multiple times
    for i in range(3):
        await agent.prompt(
            prompt=[TextContentBlock(text=f"Request {i+1}", type="text")],
            session_id=session_id,
        )

    print(f"\nPrompt calls: 3")
    print(
        f"Additional discovery calls: {len(fake.discover_tools_calls) - initial_discovery_calls}"
    )
    print(f"✓ No re-discovery occurred (cached state reused)")

    # ============================================================
    # PART 3: Lazy Fallback for Unknown Sessions
    # ============================================================

    print("\n=== Lazy Fallback ===")

    # Call prompt() with session_id that wasn't registered via new_session()
    unknown_session_id = "lazy-session-123"

    print(f"Calling prompt() with unknown session_id: {unknown_session_id}")

    before_calls = len(fake.discover_tools_calls)
    await agent.prompt(
        prompt=[TextContentBlock(text="Lazy discovery", type="text")],
        session_id=unknown_session_id,
    )

    print(f"Discovery calls after lazy fallback: {len(fake.discover_tools_calls) - before_calls}")
    print(f"✓ Lazy discovery triggered and result cached")

    # Second call to same unknown session should use cached state
    before_calls = len(fake.discover_tools_calls)
    await agent.prompt(
        prompt=[TextContentBlock(text="Lazy discovery again", type="text")],
        session_id=unknown_session_id,
    )

    print(
        f"Discovery calls on second prompt: {len(fake.discover_tools_calls) - before_calls}"
    )
    print(f"✓ Lazy-discovered state was cached and reused")

    # ============================================================
    # PART 4: Three-Tier Fallback
    # ============================================================

    print("\n=== Three-Tier Fallback ===")

    # Tier 1: Full catalog
    fake1 = FakeClient(tool_catalog=tool_catalog)
    agent1 = PunieAgent(model="test")
    agent1.on_connect(fake1)
    await agent1.initialize(protocol_version=1)
    resp1 = await agent1.new_session(cwd="/tmp", mcp_servers=[])
    state1 = agent1._sessions[resp1.session_id]
    print(f"Tier 1 (catalog): {state1.discovery_tier}, tools={len(state1.catalog.tools) if state1.catalog else 0}")

    # Tier 2: Capabilities fallback
    fake2 = FakeClient(
        tool_catalog=[],
        capabilities=ClientCapabilities(fs=FileSystemCapability(read_text_file=True)),
    )
    agent2 = PunieAgent(model="test")
    agent2.on_connect(fake2)
    await agent2.initialize(
        protocol_version=1,
        client_capabilities=ClientCapabilities(fs=FileSystemCapability(read_text_file=True)),
    )
    resp2 = await agent2.new_session(cwd="/tmp", mcp_servers=[])
    state2 = agent2._sessions[resp2.session_id]
    print(f"Tier 2 (capabilities): {state2.discovery_tier}, catalog={state2.catalog}")

    # Tier 3: Default fallback
    fake3 = FakeClient(tool_catalog=[])
    agent3 = PunieAgent(model="test")
    agent3.on_connect(fake3)
    await agent3.initialize(protocol_version=1)
    resp3 = await agent3.new_session(cwd="/tmp", mcp_servers=[])
    state3 = agent3._sessions[resp3.session_id]
    print(f"Tier 3 (default): {state3.discovery_tier}, catalog={state3.catalog}")

    print("\n✓ Session registration demonstrated")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
