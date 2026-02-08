"""PunieAgent adapter for bridging ACP Agent protocol to Pydantic AI.

PunieAgent implements all 14 methods of the ACP Agent protocol while delegating
prompt handling to a Pydantic AI Agent. This adapter pattern allows Punie to
speak ACP externally (to PyCharm) while using Pydantic AI internally (for LLM
interaction).

The adapter supports dynamic tool discovery via a three-tier fallback:
1. Catalog-based (discover_tools() returns tool descriptors)
2. Capability-based (client_capabilities flags)
3. Default (all 7 static tools)
"""

import logging
from typing import Any, cast

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models import KnownModelName, Model
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
from .discovery import parse_tool_catalog
from .factory import create_pydantic_agent
from .toolset import create_toolset, create_toolset_from_capabilities, create_toolset_from_catalog

logger = logging.getLogger(__name__)


class PunieAgent:
    """Adapter that bridges ACP Agent protocol to Pydantic AI.

    Implements all 14 methods of the ACP Agent protocol. The prompt() method
    delegates to Pydantic AI Agent.run(), while other methods provide
    sensible defaults.

    Supports dynamic tool discovery:
    - Stores client_capabilities from initialize()
    - Calls discover_tools() if available (Tier 1)
    - Falls back to capabilities (Tier 2)
    - Falls back to all static tools (Tier 3)

    Args:
        model: Model name or instance (for per-session agent construction).
               For backward compatibility, can also accept a PydanticAgent instance.
        name: Agent name for identification
        usage_limits: Optional usage limits for token/request control
    """

    def __init__(
        self,
        model: KnownModelName | Model | PydanticAgent[ACPDeps, str] = "test",
        name: str = "punie-agent",
        usage_limits: UsageLimits | None = None,
    ) -> None:
        # Backward compatibility: support passing PydanticAgent instance
        if isinstance(model, PydanticAgent):
            self._model = "test"  # Default model for legacy usage
            self._legacy_agent = model  # Store for legacy tests
        else:
            self._model = model
            self._legacy_agent = None

        self._name = name
        self._usage_limits = usage_limits
        self._next_session_id = 0
        self._conn: Client | None = None
        self._client_capabilities: ClientCapabilities | None = None
        self._client_info: Implementation | None = None

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
        """Initialize the agent connection.

        Stores client capabilities and info for later use in dynamic tool discovery.
        """
        self._client_capabilities = client_capabilities
        self._client_info = client_info
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
        constructs ACPDeps, builds session-specific toolset via discovery, and
        delegates to Pydantic AI Agent.run().

        Three-tier toolset discovery:
        1. Call discover_tools() if available (IDE advertises tools)
        2. Use client_capabilities if no discovery (capability flags)
        3. Use all 7 static tools if no capabilities (backward compat)
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

        # Use legacy agent if available (backward compatibility)
        pydantic_agent: PydanticAgent[ACPDeps, str]
        if self._legacy_agent:
            # Type checker can't narrow the union properly, but we know it's correct
            pydantic_agent = self._legacy_agent  # ty: ignore[invalid-assignment]
        else:
            # Build session-specific toolset via discovery
            toolset = None
            try:
                # Tier 1: Try discovery
                if hasattr(conn, "discover_tools"):
                    catalog_dict = await conn.discover_tools(session_id=session_id)
                    if catalog_dict and catalog_dict.get("tools"):
                        catalog = parse_tool_catalog(catalog_dict)
                        toolset = create_toolset_from_catalog(catalog)
                        tool_names = [t.name for t in catalog.tools]
                        logger.info(
                            f"Built toolset from catalog: {len(catalog.tools)} tools - {tool_names}"
                        )
            except Exception as exc:
                logger.warning(f"Tool discovery failed, falling back: {exc}")

            # Tier 2: Capabilities fallback
            if toolset is None and self._client_capabilities:
                toolset = create_toolset_from_capabilities(self._client_capabilities)
                tool_names = list(toolset.tools.keys())
                logger.info(
                    f"Built toolset from capabilities: {len(tool_names)} tools - {tool_names}"
                )

            # Tier 3: Default fallback
            if toolset is None:
                toolset = create_toolset()
                tool_names = list(toolset.tools.keys())
                logger.info(
                    f"Using default toolset: {len(tool_names)} tools - {tool_names}"
                )

            # Construct per-session Pydantic AI agent
            # Cast is safe: __init__ ensures self._model is KnownModelName | Model when not legacy
            model_value = cast(KnownModelName | Model, self._model)
            pydantic_agent = create_pydantic_agent(model=model_value, toolset=toolset)

        # Delegate to Pydantic AI with error handling
        try:
            result = await pydantic_agent.run(
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
