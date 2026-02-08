"""PunieAgent adapter for bridging ACP Agent protocol to Pydantic AI.

PunieAgent implements all 14 methods of the ACP Agent protocol while delegating
prompt handling to a Pydantic AI Agent. This adapter pattern allows Punie to
speak ACP externally (to PyCharm) while using Pydantic AI internally (for LLM
interaction).
"""

import logging
from typing import Any

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from punie.acp import (
    PROTOCOL_VERSION,
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
    text_block,
    update_agent_message,
)
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.acp.interfaces import Client
from punie.acp.schema import (
    AgentCapabilities,
    AudioContentBlock,
    ClientCapabilities,
    EmbeddedResourceContentBlock,
    HttpMcpServer,
    ImageContentBlock,
    Implementation,
    McpServerStdio,
    ResourceContentBlock,
    SseMcpServer,
    TextContentBlock,
)

from .deps import ACPDeps

logger = logging.getLogger(__name__)


class PunieAgent:
    """Adapter that bridges ACP Agent protocol to Pydantic AI.

    Implements all 14 methods of the ACP Agent protocol. The prompt() method
    delegates to Pydantic AI Agent.arun(), while other methods provide
    sensible defaults.

    Args:
        pydantic_agent: Pydantic AI Agent instance
        name: Agent name for identification
        usage_limits: Optional usage limits for token/request control
    """

    def __init__(
        self,
        pydantic_agent: PydanticAgent[ACPDeps, str],
        name: str = "punie-agent",
        usage_limits: UsageLimits | None = None,
    ) -> None:
        self._pydantic_agent = pydantic_agent
        self._name = name
        self._usage_limits = usage_limits
        self._next_session_id = 0
        self._sessions: set[str] = set()
        self._conn: Client | None = None

    def on_connect(self, conn: Client) -> None:
        """Called when client connects."""
        self._conn = conn

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        """Initialize the agent connection."""
        return InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_capabilities=AgentCapabilities(),
            agent_info=Implementation(
                name=self._name,
                title="Punie AI Coding Agent",
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
        session_id = f"punie-session-{self._next_session_id}"
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
        prompt: list[
            TextContentBlock
            | ImageContentBlock
            | AudioContentBlock
            | ResourceContentBlock
            | EmbeddedResourceContentBlock
        ],
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        """Process a prompt and return response.

        This is the core integration point. Extracts text from ACP prompt blocks,
        constructs ACPDeps, and delegates to Pydantic AI Agent.run().
        """
        # Extract text from prompt blocks
        prompt_text = ""
        for block in prompt:
            if isinstance(block, TextContentBlock):
                prompt_text += block.text

        # Construct dependencies for Pydantic AI
        conn = self._conn
        if not conn:
            raise RuntimeError("No client connection established")

        deps = ACPDeps(
            client_conn=conn,
            session_id=session_id,
            tracker=ToolCallTracker(),
        )

        # Delegate to Pydantic AI with error handling
        try:
            result = await self._pydantic_agent.run(
                prompt_text, deps=deps, usage_limits=self._usage_limits
            )
            response_text = result.output

        except UsageLimitExceeded as exc:
            response_text = f"Usage limit exceeded: {exc}"

        except Exception as exc:
            logger.exception("Agent run failed")
            response_text = f"Agent error: {exc}"

        await conn.session_update(
            session_id,
            update_agent_message(text_block(response_text)),
        )
        return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        """Cancel a running prompt."""
        pass

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle extension methods."""
        return {"echo": params}

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        """Handle extension notifications."""
        pass
