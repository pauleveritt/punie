"""Pytest configuration and fixtures."""

from collections.abc import AsyncGenerator, Callable

import pytest_asyncio
from sybil import Sybil
from sybil.parsers.myst import PythonCodeBlockParser

from acp.core import AgentSideConnection, ClientSideConnection
from tests.acp_helpers import FakeAgent, FakeClient, _Server

# Sybil configuration for MyST doctest integration
pytest_collect_file = Sybil(
    parsers=[PythonCodeBlockParser()],
    patterns=["*.md"],
).pytest()


@pytest_asyncio.fixture
async def server() -> AsyncGenerator[_Server, None]:
    """Provides a server-client connection pair for testing."""
    async with _Server() as server_instance:
        yield server_instance


@pytest_asyncio.fixture
def agent() -> FakeAgent:
    """Returns a FakeAgent instance for testing."""
    return FakeAgent()


@pytest_asyncio.fixture
def client() -> FakeClient:
    """Returns a FakeClient instance for testing."""
    return FakeClient()


@pytest_asyncio.fixture
def connect(
    server, agent, client
) -> Callable[[bool, bool], tuple[AgentSideConnection, ClientSideConnection]]:
    """Factory fixture that creates wired ACP connections over TCP loopback.

    Args:
        connect_agent: Whether to create agent-side connection
        connect_client: Whether to create client-side connection
        use_unstable_protocol: Whether to use unstable protocol features

    Returns:
        Tuple of (AgentSideConnection, ClientSideConnection)
    """

    def _connect(
        connect_agent: bool = True,
        connect_client: bool = True,
        use_unstable_protocol: bool = False,
    ) -> tuple[AgentSideConnection, ClientSideConnection]:
        agent_conn = None
        client_conn = None
        if connect_agent:
            agent_conn = AgentSideConnection(
                agent,
                server.server_writer,
                server.server_reader,
                listening=True,
                use_unstable_protocol=use_unstable_protocol,
            )
        if connect_client:
            client_conn = ClientSideConnection(
                client,
                server.client_writer,
                server.client_reader,
                use_unstable_protocol=use_unstable_protocol,
            )
        return agent_conn, client_conn  # type: ignore[return-value]

    return _connect
