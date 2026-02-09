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

from punie.agent.deps import ACPDeps
from punie.agent.discovery import ToolCatalog, parse_tool_catalog
from punie.agent.factory import create_pydantic_agent
from punie.agent.session import SessionState
from punie.agent.toolset import (
    create_toolset,
    create_toolset_from_capabilities,
    create_toolset_from_catalog,
)

logger = logging.getLogger(__name__)


def _get_agent_tool_names(agent: PydanticAgent[Any, Any]) -> list[str]:
    """Get tool names from a pydantic-ai Agent's user toolsets."""
    names: list[str] = []
    for ts in agent._user_toolsets:
        if hasattr(ts, "tools"):
            names.extend(ts.tools.keys())
    return names


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
        logger.info("=== PunieAgent.__init__() called ===")
        logger.info(f"Model: {model}")
        logger.info(f"Name: {name}")
        logger.info(f"Usage limits: {usage_limits}")

        # Backward compatibility: support passing PydanticAgent instance
        if isinstance(model, PydanticAgent):
            logger.info("Legacy mode: PydanticAgent instance provided")
            self._model = "test"  # Default model for legacy usage
            self._legacy_agent = model  # Store for legacy tests
        else:
            logger.info(f"Normal mode: model={model}")
            self._model = model
            self._legacy_agent = None

        self._name = name
        self._usage_limits = usage_limits
        self._next_session_id = 0
        self._conn: Client | None = None
        self._client_capabilities: ClientCapabilities | None = None
        self._client_info: Implementation | None = None
        self._sessions: dict[str, SessionState] = {}
        self._greeted_sessions: set[str] = set()  # Track which sessions got greeting
        self._pending_errors: dict[str, str] = {}  # Store errors to send during first prompt
        logger.info("=== PunieAgent.__init__() complete ===")


    def on_connect(self, conn: Client) -> None:
        """Called when client connects."""
        logger.info("=== on_connect() called ===")
        logger.info(f"Connection type: {type(conn).__name__}")
        logger.info(f"Connection object: {conn}")
        self._conn = conn
        logger.info("=== on_connect() complete ===")


    async def _discover_and_build_toolset(self, session_id: str) -> SessionState:
        """Discover tools and build session state.

        Implements three-tier discovery:
        1. Tier 1: Full catalog from discover_tools()
        2. Tier 2: Fallback to client capabilities (filesystem-only)
        3. Tier 3: Default toolset (all 7 static tools)

        Returns immutable SessionState with catalog, agent, and discovery tier.

        >>> # This is an internal helper, called from new_session()
        >>> # See examples/10_session_registration.py for usage
        """
        try:
            logger.info(f"=== _discover_and_build_toolset() for session {session_id} ===")
            logger.info(f"Connection available: {self._conn is not None}")
            logger.info(f"Model: {self._model}")

            if not self._conn:
                # No connection: return Tier 3 default
                logger.info("No connection, using Tier 3 default toolset")
                toolset = create_toolset()
                model_value = cast(KnownModelName | Model, self._model)
                pydantic_agent = create_pydantic_agent(model=model_value, toolset=toolset)
                logger.info("Tier 3 agent created successfully")
                return SessionState(catalog=None, agent=pydantic_agent, discovery_tier=3)

            catalog: ToolCatalog | None = None
            toolset = None
            discovery_tier = 3

            try:
                # Tier 1: Try discovery
                logger.info("Checking for discover_tools method...")
                if hasattr(self._conn, "discover_tools"):
                    logger.info("discover_tools method found, calling it...")
                    catalog_dict = await self._conn.discover_tools(session_id=session_id)
                    logger.info(f"discover_tools returned: {catalog_dict}")
                    if catalog_dict and catalog_dict.get("tools"):
                        logger.info("Parsing tool catalog...")
                        catalog = parse_tool_catalog(catalog_dict)
                        logger.info("Creating toolset from catalog...")
                        toolset = create_toolset_from_catalog(catalog)
                        discovery_tier = 1
                        tool_names = [t.name for t in catalog.tools]
                        logger.info(
                            f"Built toolset from catalog: {len(catalog.tools)} tools - {tool_names}"
                        )
                    else:
                        logger.info("discover_tools returned empty or invalid catalog")
                else:
                    logger.info("discover_tools method not available")
            except Exception as exc:
                logger.warning(f"Tool discovery failed, falling back: {exc}")
                logger.exception("Full discovery exception:")

            # Tier 2: Capabilities fallback
            if toolset is None and self._client_capabilities:
                logger.info("Using Tier 2: capabilities-based toolset")
                candidate = create_toolset_from_capabilities(self._client_capabilities)
                if candidate.tools:
                    toolset = candidate
                    discovery_tier = 2
                    tool_names = list(toolset.tools.keys())
                    logger.info(
                        f"Built toolset from capabilities: {len(tool_names)} tools - {tool_names}"
                    )
                else:
                    logger.info("Tier 2 produced empty toolset, falling through to Tier 3")

            # Tier 3: Default fallback
            if toolset is None:
                logger.info("Using Tier 3: default toolset")
                toolset = create_toolset()
                discovery_tier = 3
                tool_names = list(toolset.tools.keys())
                logger.info(
                    f"Using default toolset: {len(tool_names)} tools - {tool_names}"
                )

            # Construct per-session Pydantic AI agent
            logger.info(f"Creating Pydantic AI agent with model: {self._model}")
            # Cast is safe: __init__ ensures self._model is KnownModelName | Model when not legacy
            model_value = cast(KnownModelName | Model, self._model)

            try:
                pydantic_agent = create_pydantic_agent(model=model_value, toolset=toolset)
                logger.info("Pydantic AI agent created successfully")
            except ImportError as exc:
                # Handle missing mlx-lm gracefully
                if "mlx-lm" in str(exc):
                    error_msg = (
                        "⚠️ **Local model support not available**\n\n"
                        f"Your configuration is set to use model `{self._model}`, but the required "
                        "`mlx-lm` package is not installed.\n\n"
                        "**To fix this, choose one of these options:**\n\n"
                        "1. **Use the test model (recommended for development):**\n"
                        "   ```bash\n"
                        "   uv run punie init --model test\n"
                        "   ```\n"
                        "   Then restart PyCharm's agent connection.\n\n"
                        "2. **Install local model support:**\n"
                        "   ```bash\n"
                        "   uv pip install 'punie[local]'\n"
                        "   punie download-model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit\n"
                        "   ```\n\n"
                        "3. **Use a cloud model:**\n"
                        "   ```bash\n"
                        "   uv run punie init --model openai:gpt-4o\n"
                        "   ```\n"
                        "   (Requires OPENAI_API_KEY environment variable)\n\n"
                        "Falling back to test model for this session..."
                    )
                    logger.error(error_msg)

                    # Store error to send during first prompt (avoids protocol issues)
                    self._pending_errors[session_id] = error_msg
                    logger.info("Stored mlx-lm error to send during first prompt")

                    # Fall back to test model
                    logger.info("Falling back to test model...")
                    pydantic_agent = create_pydantic_agent(model="test", toolset=toolset)
                    logger.info("Fallback to test model successful")
                else:
                    # Other ImportError, re-raise
                    raise

            state = SessionState(
                catalog=catalog, agent=pydantic_agent, discovery_tier=discovery_tier
            )
            logger.info(f"=== _discover_and_build_toolset() complete, tier={discovery_tier} ===")
            return state
        except Exception as exc:
            logger.exception("CRITICAL: _discover_and_build_toolset() failed")
            logger.error(f"Exception type: {type(exc).__name__}")
            logger.error(f"Exception message: {str(exc)}")
            raise

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
        try:
            logger.info("=== initialize() called ===")
            logger.info(f"Protocol version: {protocol_version}")
            logger.info(f"Client capabilities: {client_capabilities}")
            logger.info(f"Client info: {client_info}")
            logger.info(f"Additional kwargs: {kwargs}")

            self._client_capabilities = client_capabilities
            self._client_info = client_info

            response = InitializeResponse(
                protocol_version=PROTOCOL_VERSION,
                agent_capabilities=AgentCapabilities(),
                agent_info=Implementation(
                    name=self._name,
                    title="Punie AI Coding Agent",
                    version="0.1.0",
                ),
            )
            logger.info(f"initialize() successful, returning: {response}")
            logger.info("=== initialize() complete ===")
            return response
        except Exception as exc:
            logger.exception("CRITICAL: initialize() failed with exception")
            logger.error(f"Exception type: {type(exc).__name__}")
            logger.error(f"Exception message: {str(exc)}")
            raise

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        **kwargs: Any,
    ) -> NewSessionResponse:
        """Create a new session and register tools.

        Discovers tools once and caches the result for the session lifetime.
        Skips registration if legacy agent mode is active or no connection.
        """
        try:
            logger.info("=== new_session() called ===")
            logger.info(f"Current working directory: {cwd}")
            logger.info(f"MCP servers count: {len(mcp_servers)}")
            logger.info(f"Legacy agent mode: {self._legacy_agent is not None}")
            logger.info(f"Connection established: {self._conn is not None}")

            session_id = f"punie-session-{self._next_session_id}"
            self._next_session_id += 1
            logger.info(f"Generated session_id: {session_id}")

            # Greeting is now sent during first prompt() call to avoid protocol issues

            # Register tools if not in legacy mode and connection exists
            if not self._legacy_agent and self._conn:
                logger.info("Starting tool registration...")
                state = await self._discover_and_build_toolset(session_id)
                self._sessions[session_id] = state
                tool_names = _get_agent_tool_names(state.agent)
                tool_count = len(tool_names)
                logger.info(
                    f"Registered session {session_id}: Tier {state.discovery_tier}, "
                    f"{tool_count} tools"
                )
            else:
                logger.info("Skipping tool registration (legacy mode or no connection)")

            response = NewSessionResponse(session_id=session_id)
            logger.info(f"new_session() successful, returning: {response}")
            logger.info("=== new_session() complete ===")
            return response
        except Exception as exc:
            logger.exception("CRITICAL: new_session() failed with exception")
            logger.error(f"Exception type: {type(exc).__name__}")
            logger.error(f"Exception message: {str(exc)}")
            raise

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
        from punie.acp.helpers import text_block, update_agent_message, update_agent_message_text

        logger.info(f"=== prompt() called for session {session_id} ===")

        # Extract text from prompt blocks
        prompt_text = ""
        for block in prompt:
            if isinstance(block, TextContentBlock):
                prompt_text += block.text

        logger.info(
            f"Extracted prompt text ({len(prompt_text)} chars): {prompt_text[:200]}..."
        )

        # Send any pending errors and greeting for first prompt in session
        if session_id not in self._greeted_sessions and self._conn:
            # Send pending errors first (e.g., mlx-lm missing)
            if session_id in self._pending_errors:
                error_msg = self._pending_errors[session_id]
                logger.info("Sending pending error message to client")
                try:
                    await self._conn.session_update(
                        session_id, update_agent_message(text_block(error_msg))
                    )
                    logger.info("Pending error sent successfully")
                    del self._pending_errors[session_id]
                except Exception as error_exc:
                    logger.warning(f"Failed to send pending error: {error_exc}")

            # Send greeting
            logger.info(f"Sending greeting for first prompt in session {session_id}")
            try:
                greeting = (
                    "👋 **Punie Agent Connected**\n\n"
                    f"Model: `{self._model}`\n"
                    "Ready to assist with your coding tasks!\n\n"
                    "---\n\n"
                )
                await self._conn.session_update(
                    session_id, update_agent_message_text(greeting)
                )
                self._greeted_sessions.add(session_id)
                logger.info("Greeting sent successfully")
            except Exception as greeting_exc:
                logger.warning(f"Failed to send greeting: {greeting_exc}")

        # Construct dependencies for Pydantic AI
        conn = self._conn
        if not conn:
            logger.error("No client connection established")
            raise RuntimeError("No client connection established")

        deps = ACPDeps(
            client_conn=conn,
            session_id=session_id,
            tracker=ToolCallTracker(),
        )
        logger.debug(f"Created ACPDeps for session {session_id}")

        # Use cached session state or lazy fallback
        pydantic_agent: PydanticAgent[ACPDeps, str]
        if self._legacy_agent:
            # Legacy mode: use pre-constructed agent
            logger.info("Using legacy agent mode")
            pydantic_agent = self._legacy_agent  # ty: ignore[invalid-assignment]
        elif session_id in self._sessions:
            # Use cached session state (registered in new_session)
            state = self._sessions[session_id]
            logger.info(f"Using cached session state (Tier {state.discovery_tier})")
            pydantic_agent = state.agent
        else:
            # Lazy fallback for callers that skip new_session()
            logger.info("No cached session, performing lazy registration")
            state = await self._discover_and_build_toolset(session_id)
            self._sessions[session_id] = state
            pydantic_agent = state.agent
            logger.info(
                f"Lazy registration for session {session_id}: Tier {state.discovery_tier}"
            )

        # Log model and tool information
        logger.info(f"Agent model: {pydantic_agent.model}")
        tool_names = _get_agent_tool_names(pydantic_agent)
        logger.info(f"Agent tools available: {tool_names}")

        # Delegate to Pydantic AI with error handling
        logger.info("Calling pydantic_agent.run()...")
        try:
            result = await pydantic_agent.run(
                prompt_text, deps=deps, usage_limits=self._usage_limits
            )
            response_text = result.output
            logger.info(
                f"Agent run successful, response length: {len(response_text)} chars"
            )
            logger.info(f"Response preview: {response_text[:200]}...")

            # Log usage info if available
            if result.usage():
                usage = result.usage()
                logger.info(
                    f"Token usage - requests: {usage.requests}, total tokens: {usage.total_tokens}"
                )

        except UsageLimitExceeded as exc:
            logger.error(f"Usage limit exceeded: {exc}")
            response_text = f"Usage limit exceeded: {exc}"

        except Exception as exc:
            logger.exception("Agent run failed")
            response_text = f"Agent error: {exc}"

        logger.info("Sending session_update to client...")
        await conn.session_update(
            session_id,
            update_agent_message(text_block(response_text)),
        )
        logger.info(f"=== prompt() complete for session {session_id} ===")
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
