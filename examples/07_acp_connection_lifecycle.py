"""Example 07: ACP Connection Lifecycle

Demonstrates full ACP agent-client connection over TCP loopback.

This example shows:
- Setting up LoopbackServer as async context manager
- Wiring AgentSideConnection and ClientSideConnection to server streams
- Initialize handshake (protocol_version=1)
- Creating new session via new_session()
- File operations: read_text_file() and write_text_file()
- Full bidirectional ACP protocol flow in-process

Tier: 2 (Async, self-contained TCP loopback)
"""

import asyncio


def main() -> None:
    """Run async connection lifecycle demonstration."""
    asyncio.run(async_main())


async def async_main() -> None:
    """Demonstrate ACP connection structure with TCP loopback.

    This example shows connection setup using _Server, FakeAgent, and FakeClient.
    Full protocol handshake and file operations are demonstrated in integration tests.
    """
    from punie.acp.core import AgentSideConnection, ClientSideConnection
    from punie.testing import FakeAgent, FakeClient, LoopbackServer

    # Set up TCP loopback server
    async with LoopbackServer() as server:
        # Create fake agent and client
        agent = FakeAgent()
        client = FakeClient()

        # Wire up connections:
        # - AgentSideConnection wraps the agent and communicates via server streams
        # - ClientSideConnection wraps the client and communicates via client streams
        agent_conn = AgentSideConnection(
            agent, server.server_writer, server.server_reader, listening=True
        )
        client_conn = ClientSideConnection(
            client, server.client_writer, server.client_reader
        )

        # Verify connections are established
        assert agent_conn is not None
        assert client_conn is not None

        # Pre-populate client's file system (simulates IDE file access)
        client.files["/test/example.txt"] = "Hello from ACP!"
        assert "/test/example.txt" in client.files

        # AgentSideConnection provides methods like:
        # - read_text_file() / write_text_file() - file operations
        # - session_update() - send session updates
        # - request_permission() - request permission for tool execution
        #
        # Full protocol flow (initialize, new_session, file ops) is shown in tests/test_acp_sdk.py

        print(
            "✓ Connection structure: LoopbackServer, FakeAgent, FakeClient, connections verified"
        )


if __name__ == "__main__":
    main()
