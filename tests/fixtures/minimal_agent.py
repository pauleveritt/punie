"""Minimal ACP agent for stdio integration testing.

This agent implements the bare minimum ACP protocol to test stdio connections.
It can be spawned as a subprocess and communicated with via stdin/stdout.
"""

import asyncio
from typing import Any

from punie.acp import (
    PROTOCOL_VERSION,
    Agent,
    AuthenticateResponse,
    ForkSessionResponse,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    ResumeSessionResponse,
    SetSessionModelResponse,
    SetSessionModeResponse,
    run_agent,
    text_block,
    update_agent_message,
)
from punie.acp.interfaces import Client
from punie.acp.schema import (
    AgentCapabilities,
    ClientCapabilities,
    HttpMcpServer,
    Implementation,
    McpServerStdio,
    SseMcpServer,
)


class MinimalAgent(Agent):
    """Minimal agent implementation for testing stdio connections."""

    def __init__(self) -> None:
        self._next_session_id = 0
        self._sessions: set[str] = set()
        self._conn: Client | None = None

    def on_connect(self, conn: Client) -> None:
        """Called when client connects."""
        self._conn = conn

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: ClientCapabilities,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        """Initialize the agent connection."""
        return InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_capabilities=AgentCapabilities(),
            agent_info=Implementation(
                name="minimal-test-agent",
                title="Minimal Test Agent",
                version="0.1.0",
            ),
        )

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        **kwargs: Any,
    ) -> NewSessionResponse:
        """Create a new session."""
        session_id = f"test-session-{self._next_session_id}"
        self._next_session_id += 1
        self._sessions.add(session_id)
        return NewSessionResponse(session_id=session_id)

    async def load_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        session_id: str,
        **kwargs: Any,
    ) -> LoadSessionResponse:
        """Load an existing session."""
        return LoadSessionResponse()

    async def list_sessions(
        self, cursor: str | None = None, cwd: str | None = None, **kwargs: Any
    ) -> ListSessionsResponse:
        """List available sessions."""
        return ListSessionsResponse(sessions=[], next_cursor=None)

    async def set_session_mode(
        self, mode_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModeResponse:
        """Set session mode."""
        return SetSessionModeResponse()

    async def set_session_model(
        self, model_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModelResponse:
        """Set session model."""
        return SetSessionModelResponse()

    async def fork_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> ForkSessionResponse:
        """Fork an existing session."""
        forked_id = f"{session_id}-fork"
        return ForkSessionResponse(session_id=forked_id)

    async def resume_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> ResumeSessionResponse:
        """Resume an existing session."""
        return ResumeSessionResponse()

    async def authenticate(self, method_id: str, **kwargs: Any) -> AuthenticateResponse:
        """Authenticate with the agent."""
        return AuthenticateResponse()

    async def prompt(
        self,
        prompt: list,
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        """Process a prompt and return response."""
        # Echo back the prompt content
        if self._conn:
            await self._conn.session_update(
                session_id,
                update_agent_message(text_block("Echo: received prompt")),
            )

        return PromptResponse(
            stop_reason="end_turn",
            usage=None,
        )

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        """Cancel a running prompt."""
        pass

    async def ext_method(self, method: str, params: dict) -> dict:
        """Handle extension methods."""
        return {"echo": params}

    async def ext_notification(self, method: str, params: dict) -> None:
        """Handle extension notifications."""
        pass


async def main() -> None:
    """Run the minimal agent over stdio."""
    agent = MinimalAgent()
    await run_agent(agent)


if __name__ == "__main__":
    asyncio.run(main())
