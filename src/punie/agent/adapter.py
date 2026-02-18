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

import asyncio
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
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
from punie.perf import PerformanceCollector, generate_html_report

logger = logging.getLogger(__name__)


def _get_agent_tool_names(agent: PydanticAgent[Any, Any]) -> list[str]:
    """Get tool names from a pydantic-ai Agent's user toolsets."""
    names: list[str] = []
    for ts in agent._user_toolsets:
        if hasattr(ts, "tools"):
            names.extend(ts.tools.keys())  # type: ignore[attr-defined]
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
        self._pending_errors: dict[
            str, str
        ] = {}  # Store errors to send during first prompt

        # Multi-client support (Phase 28)
        self._connections: dict[str, Client] = {}  # client_id → client connection
        self._session_owners: dict[str, str] = {}  # session_id → client_id
        self._next_client_id = 0  # For unique client IDs

        # Reconnection support (Phase 28.1)
        self._disconnected_clients: dict[str, float] = {}  # client_id → disconnect_time
        self._session_tokens: dict[str, str] = {}  # session_id → resume_token
        self._grace_period = 300  # 5 minutes to reconnect
        self._resuming_sessions: dict[str, float] = {}  # Issue #9: session_id → resume_start_time

        # Issue #7: Add locks to protect shared state
        self._state_lock = asyncio.Lock()  # Protects all dictionaries

        # Cleanup task (started lazily when event loop is running)
        self._cleanup_task: asyncio.Task[None] | None = None
        self._cleanup_started = False

        # Performance reporting via PUNIE_PERF env var
        # TODO: Re-enable after fixing collector lifecycle issues
        # Temporarily disabled due to infinite loop when reusing collectors across prompts
        self._perf_enabled = False  # os.getenv("PUNIE_PERF", "0") == "1"
        self._perf_collectors: dict[
            str, PerformanceCollector
        ] = {}  # Per-session collectors
        if self._perf_enabled:
            logger.info("Performance reporting enabled via PUNIE_PERF=1")

        logger.info("=== PunieAgent.__init__() complete ===")

    async def shutdown(self) -> None:
        """Shutdown agent and cleanup tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Agent shutdown complete")

    async def _cleanup_expired_sessions(self) -> None:
        """Background task to clean up expired disconnected sessions."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                current_time = time.time()

                async with self._state_lock:
                    # Find expired disconnected clients
                    expired = [
                        client_id
                        for client_id, disconnect_time in self._disconnected_clients.items()
                        if current_time - disconnect_time > self._grace_period
                    ]

                    # Expire stuck resuming sessions (sessions that have been in
                    # _resuming_sessions longer than grace_period without completing)
                    stuck_resuming = [
                        sid for sid, start_time in self._resuming_sessions.items()
                        if current_time - start_time > self._grace_period
                    ]
                    for sid in stuck_resuming:
                        logger.warning(
                            f"Session {sid} stuck in resuming state for >{self._grace_period}s, "
                            "removing from resuming set"
                        )
                        del self._resuming_sessions[sid]

                    # Clean up expired sessions
                    for client_id in expired:
                        logger.info(f"Cleaning up expired client {client_id}")

                        # Find sessions owned by this client
                        # Skip sessions currently being resumed (within TTL)
                        sessions_to_remove = [
                            sid for sid, owner in self._session_owners.items()
                            if owner == client_id and sid not in self._resuming_sessions
                        ]

                        for session_id in sessions_to_remove:
                            self._sessions.pop(session_id, None)
                            self._greeted_sessions.discard(session_id)
                            self._pending_errors.pop(session_id, None)
                            self._perf_collectors.pop(session_id, None)
                            self._session_tokens.pop(session_id, None)
                            del self._session_owners[session_id]

                        # Only remove client if all sessions were cleaned up
                        # (if some sessions are being resumed, keep client in grace period)
                        remaining_sessions = [
                            sid for sid, owner in self._session_owners.items()
                            if owner == client_id
                        ]
                        if not remaining_sessions:
                            del self._disconnected_clients[client_id]
                            logger.info(
                                f"Expired cleanup: {client_id}, removed {len(sessions_to_remove)} sessions"
                            )
                        else:
                            logger.info(
                                f"Client {client_id} still has {len(remaining_sessions)} sessions being resumed, keeping in grace period"
                            )

            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as exc:
                logger.exception(f"Error in cleanup task: {exc}")

    def on_connect(self, conn: Client) -> None:
        """Called when client connects."""
        logger.info("=== on_connect() called ===")
        logger.info(f"Connection type: {type(conn).__name__}")
        logger.info(f"Connection object: {conn}")
        self._conn = conn
        logger.info("=== on_connect() complete ===")

    async def register_client(self, client_conn: Client) -> str:
        """Register a new client connection.

        Args:
            client_conn: Client connection instance (e.g., WebSocket wrapper).

        Returns:
            Unique client ID for this connection.
        """
        # Start cleanup task on first client registration (lazy initialization)
        if not self._cleanup_started and not self._legacy_agent:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            self._cleanup_started = True
            logger.info("Started session cleanup task")

        # Issue #6: Atomic registration to prevent race condition
        async with self._state_lock:
            client_id = f"client-{self._next_client_id}"
            self._next_client_id += 1
            self._connections[client_id] = client_conn
            logger.info(f"Registered client {client_id}")
            return client_id

    async def unregister_client(self, client_id: str, allow_reconnect: bool = True) -> None:
        """Unregister a client and optionally preserve sessions for reconnection.

        Args:
            client_id: Client ID to unregister.
            allow_reconnect: If True, preserve sessions for grace period (default: True).
        """
        # Issue #7: Protect with lock
        async with self._state_lock:
            if client_id not in self._connections:
                logger.warning(f"Attempted to unregister unknown client {client_id}")
                return

            # Remove client connection
            del self._connections[client_id]

            if allow_reconnect:
                # Mark as disconnected but keep sessions alive
                self._disconnected_clients[client_id] = time.time()
                logger.info(
                    f"Client {client_id} disconnected, sessions preserved for {self._grace_period}s"
                )
            else:
                # Immediate cleanup (no reconnection allowed)
                sessions_to_remove = [
                    sid for sid, owner in self._session_owners.items() if owner == client_id
                ]
                for session_id in sessions_to_remove:
                    logger.info(f"Cleaning up session {session_id} owned by {client_id}")
                    # Issue #8: Remove sessions from _sessions dict (prevents stale reuse)
                    self._sessions.pop(session_id, None)
                    self._greeted_sessions.discard(session_id)
                    self._pending_errors.pop(session_id, None)
                    self._perf_collectors.pop(session_id, None)
                    self._session_tokens.pop(session_id, None)
                    del self._session_owners[session_id]

                logger.info(
                    f"Unregistered client {client_id}, cleaned up {len(sessions_to_remove)} sessions"
                )

    def get_client_connection(self, session_id: str) -> Client | None:
        """Get the client connection that owns this session.

        Args:
            session_id: Session ID to look up.

        Returns:
            Client connection for the owning client, or None if not found.
        """
        client_id = self._session_owners.get(session_id)
        if not client_id:
            return None
        return self._connections.get(client_id)

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
            logger.info(
                f"=== _discover_and_build_toolset() for session {session_id} ==="
            )
            logger.info(f"Connection available: {self._conn is not None}")
            logger.info(f"WebSocket clients: {len(self._connections)}")
            logger.info(f"Model: {self._model}")

            # Check if we have any connection (stdio or WebSocket)
            # For WebSocket, self._conn is None but we still want to create a toolset
            has_any_connection = self._conn is not None or len(self._connections) > 0

            if not has_any_connection:
                # No connection: return Tier 3 default
                logger.info("No connection, using Tier 3 default toolset")
                toolset = create_toolset()
                model_value = cast(KnownModelName | Model, self._model)
                # Create collector if perf enabled
                perf_collector = PerformanceCollector() if self._perf_enabled else None
                if perf_collector:
                    self._perf_collectors[session_id] = perf_collector
                pydantic_agent = create_pydantic_agent(
                    model=model_value, toolset=toolset, perf_collector=perf_collector
                )
                logger.info("Tier 3 agent created successfully")
                return SessionState(
                    catalog=None, agent=pydantic_agent, discovery_tier=3
                )

            catalog: ToolCatalog | None = None
            toolset = None
            discovery_tier = 3

            try:
                # Tier 1: Try discovery
                logger.info("Checking for discover_tools method...")
                if hasattr(self._conn, "discover_tools"):
                    logger.info("discover_tools method found, calling it...")
                    catalog_dict = await self._conn.discover_tools(
                        session_id=session_id
                    )
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
                    logger.info(
                        "Tier 2 produced empty toolset, falling through to Tier 3"
                    )

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

            # Create collector if perf enabled (one per session)
            perf_collector = PerformanceCollector() if self._perf_enabled else None
            if perf_collector:
                self._perf_collectors[session_id] = perf_collector

            try:
                pydantic_agent = create_pydantic_agent(
                    model=model_value, toolset=toolset, perf_collector=perf_collector
                )
                logger.info("Pydantic AI agent created successfully")
            except Exception as exc:
                # Handle local server connection errors gracefully
                # This catches errors when trying to connect to LM Studio or mlx-lm.server
                if isinstance(model_value, str) and "local" in model_value.lower():
                    error_msg = (
                        "⚠️ **Local model server not available**\n\n"
                        f"Your configuration is set to use model `{self._model}`, but the local "
                        "model server is not responding.\n\n"
                        "**To fix this, choose one of these options:**\n\n"
                        "1. **Start LM Studio:**\n"
                        "   - Download and install LM Studio from https://lmstudio.ai/\n"
                        "   - Load a model in the UI\n"
                        "   - Start the server (default: http://localhost:1234)\n\n"
                        "2. **Start mlx-lm.server:**\n"
                        "   ```bash\n"
                        "   uv pip install mlx-lm\n"
                        "   mlx-lm.server --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit\n"
                        "   ```\n\n"
                        "3. **Use the test model (recommended for development):**\n"
                        "   ```bash\n"
                        "   uv run punie init --model test\n"
                        "   ```\n"
                        "   Then restart PyCharm's agent connection.\n\n"
                        "4. **Use a cloud model:**\n"
                        "   ```bash\n"
                        "   uv run punie init --model openai:gpt-4o\n"
                        "   ```\n"
                        "   (Requires OPENAI_API_KEY environment variable)\n\n"
                        f"Error details: {exc}\n\n"
                        "Falling back to test model for this session..."
                    )
                    logger.error(error_msg)

                    # Store error to send during first prompt (avoids protocol issues)
                    self._pending_errors[session_id] = error_msg
                    logger.info("Stored local server error to send during first prompt")

                    # Fall back to test model
                    logger.info("Falling back to test model...")
                    pydantic_agent = create_pydantic_agent(
                        model="test", toolset=toolset, perf_collector=perf_collector
                    )
                    logger.info("Fallback to test model successful")
                else:
                    # Not a local model error, re-raise
                    raise

            state = SessionState(
                catalog=catalog, agent=pydantic_agent, discovery_tier=discovery_tier
            )
            logger.info(
                f"=== _discover_and_build_toolset() complete, tier={discovery_tier} ==="
            )
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
        client_id: str | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        """Create a new session and register tools.

        Discovers tools once and caches the result for the session lifetime.
        Skips registration if legacy agent mode is active or no connection.

        Args:
            cwd: Current working directory for the session.
            mcp_servers: List of MCP server configurations.
            client_id: Optional client ID for multi-client tracking (Phase 28).
            **kwargs: Additional parameters.

        Returns:
            NewSessionResponse with session_id.
        """
        try:
            logger.info("=== new_session() called ===")
            logger.info(f"Current working directory: {cwd}")
            logger.info(f"MCP servers count: {len(mcp_servers)}")
            logger.info(f"Client ID: {client_id}")
            logger.info(f"Legacy agent mode: {self._legacy_agent is not None}")
            logger.info(f"Connection established: {self._conn is not None}")

            # Issue #2: Require client_id for WebSocket sessions (prevent unowned sessions)
            # Exception: Allow legacy agent mode for backward compatibility
            if self._conn is None and client_id is None and not self._legacy_agent:
                raise RuntimeError(
                    "client_id is required when no stdio connection is established"
                )

            # Issue #9: Validate client_id exists
            if client_id is not None:
                async with self._state_lock:
                    if client_id not in self._connections:
                        raise RuntimeError(
                            f"Invalid client_id: {client_id} is not registered"
                        )

            # Issue #7: Protect session creation
            resume_token = None
            async with self._state_lock:
                session_id = f"punie-session-{self._next_session_id}"
                self._next_session_id += 1
                logger.info(f"Generated session_id: {session_id}")

                # Track session ownership for multi-client routing (Phase 28)
                if client_id:
                    self._session_owners[session_id] = client_id
                    # Generate resume token for session recovery
                    resume_token = secrets.token_urlsafe(32)
                    self._session_tokens[session_id] = resume_token
                    logger.info(f"Session {session_id} owned by client {client_id}")

                # If client was disconnected, remove from disconnected list (reconnected)
                if client_id and client_id in self._disconnected_clients:
                    del self._disconnected_clients[client_id]
                    logger.info(f"Client {client_id} reconnected before grace period expired")

            # Greeting is now sent during first prompt() call to avoid protocol issues

            # Register tools if not in legacy mode and connection exists
            # Note: For WebSocket clients, client_id is set but self._conn may be None
            has_connection = self._conn is not None or client_id is not None
            if not self._legacy_agent and has_connection:
                logger.info("Starting tool registration...")
                state = await self._discover_and_build_toolset(session_id)
                # Issue #7: Protect state write
                async with self._state_lock:
                    self._sessions[session_id] = state
                tool_names = _get_agent_tool_names(state.agent)
                tool_count = len(tool_names)
                logger.info(
                    f"Registered session {session_id}: Tier {state.discovery_tier}, "
                    f"{tool_count} tools"
                )
            else:
                logger.info("Skipping tool registration (legacy mode or no connection)")

            # Include resume token in response metadata for reconnection support
            field_meta = None
            if resume_token:
                field_meta = {"resume_token": resume_token}

            response = NewSessionResponse(
                session_id=session_id,
                field_meta=field_meta
            )
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
        client_id: str | None = None,
        resume_token: str | None = None,
        **kwargs: Any,
    ) -> ResumeSessionResponse:
        """Resume an existing session after reconnection.

        Args:
            cwd: Current working directory.
            session_id: Session ID to resume.
            mcp_servers: MCP server configurations (optional).
            client_id: New client ID for reconnected client.
            resume_token: Authentication token from original session.
            **kwargs: Additional parameters.

        Returns:
            ResumeSessionResponse.

        Raises:
            RuntimeError: If session not found, token invalid, or session expired.
        """
        logger.info(f"=== resume_session() called for {session_id} ===")

        async with self._state_lock:
            # Validate session exists
            if session_id not in self._sessions:
                raise RuntimeError(f"Session {session_id} not found or expired")

            # Validate resume token
            expected_token = self._session_tokens.get(session_id)
            if not expected_token or expected_token != resume_token:
                raise RuntimeError("Invalid resume token")

            # Get original owner
            original_owner = self._session_owners.get(session_id)
            if not original_owner:
                raise RuntimeError("Session has no owner (cannot resume)")

            # Check if original owner is in grace period
            if original_owner not in self._disconnected_clients:
                raise RuntimeError(
                    f"Session owner {original_owner} is not disconnected (already connected?)"
                )

            # Issue #9: Mark as being resumed to prevent cleanup race (record start time)
            self._resuming_sessions[session_id] = time.time()

            try:
                # Transfer ownership to new client_id
                if client_id:
                    logger.info(f"Transferring session {session_id} from {original_owner} to {client_id}")
                    self._session_owners[session_id] = client_id

                    # Remove old client from disconnected list
                    del self._disconnected_clients[original_owner]

                    # Clean up old client's other sessions (if any)
                    old_sessions = [
                        sid for sid, owner in self._session_owners.items()
                        if owner == original_owner and sid != session_id
                    ]
                    for sid in old_sessions:
                        self._sessions.pop(sid, None)
                        self._greeted_sessions.discard(sid)
                        self._pending_errors.pop(sid, None)
                        self._perf_collectors.pop(sid, None)
                        self._session_tokens.pop(sid, None)
                        del self._session_owners[sid]
            finally:
                # Always remove from resuming set
                self._resuming_sessions.pop(session_id, None)

        logger.info(f"Successfully resumed session {session_id}")
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
        calling_client_id: str | None = None,
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

        Args:
            prompt: List of content blocks containing the user's prompt.
            session_id: Session ID for this prompt.
            calling_client_id: ID of the client making this request (for multi-client security).
            **kwargs: Additional parameters.

        Returns:
            PromptResponse with stop_reason.

        Raises:
            RuntimeError: If session access is denied or no connection exists.
        """
        from punie.acp.helpers import (
            text_block,
            update_agent_message,
            update_agent_message_text,
        )

        logger.info(f"=== prompt() called for session {session_id} ===")

        # Extract text from prompt blocks (handle both dict and Pydantic model formats)
        prompt_text = ""
        for block in prompt:
            if isinstance(block, TextContentBlock):
                prompt_text += block.text
            elif isinstance(block, dict) and block.get("type") == "text":
                prompt_text += block.get("text", "")

        logger.info(
            f"Extracted prompt text ({len(prompt_text)} chars): {prompt_text[:200]}..."
        )

        # Issue #1: Validate session ownership (prevent cross-client access)
        async with self._state_lock:
            session_owner = self._session_owners.get(session_id)

        # If session has an owner, validate caller owns it
        if session_owner is not None:
            if calling_client_id is None:
                # stdio connection doesn't provide calling_client_id
                # Only allow if session is not owned by a WebSocket client
                if session_owner.startswith("client-"):
                    raise RuntimeError(
                        f"Session {session_id} is owned by {session_owner}, "
                        "cannot access from stdio connection"
                    )
            elif calling_client_id != session_owner:
                # Cross-client access attempt - SECURITY VIOLATION
                raise RuntimeError(
                    f"Access denied: Session {session_id} is owned by {session_owner}, "
                    f"cannot access from {calling_client_id}"
                )

        # Send any pending errors and greeting for first prompt in session
        # Issue #13: Support WebSocket greetings
        conn = self.get_client_connection(session_id) or self._conn
        if session_id not in self._greeted_sessions and conn:
            # Send pending errors first (e.g., local server not available)
            if session_id in self._pending_errors:
                error_msg = self._pending_errors[session_id]
                logger.info("Sending pending error message to client")
                try:
                    await conn.session_update(
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
                await conn.session_update(
                    session_id, update_agent_message_text(greeting)
                )
                self._greeted_sessions.add(session_id)
                logger.info("Greeting sent successfully")
            except Exception as greeting_exc:
                logger.warning(f"Failed to send greeting: {greeting_exc}")
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
        else:
            # Issue #7: Protect session read with lock
            async with self._state_lock:
                session_exists = session_id in self._sessions

            if session_exists:
                # Use cached session state (registered in new_session)
                async with self._state_lock:
                    state = self._sessions[session_id]
                logger.info(f"Using cached session state (Tier {state.discovery_tier})")
                pydantic_agent = state.agent
            else:
                # Issue #11: Lazy fallback with lock to prevent race condition
                logger.info("No cached session, performing lazy registration")
                async with self._state_lock:
                    # Double-check after acquiring lock (another request may have created it)
                    if session_id in self._sessions:
                        state = self._sessions[session_id]
                        logger.info("Session created by concurrent request, using it")
                    else:
                        # Actually create the session
                        state = await self._discover_and_build_toolset(session_id)
                        self._sessions[session_id] = state
                        logger.info(
                            f"Lazy registration for session {session_id}: Tier {state.discovery_tier}"
                        )
                pydantic_agent = state.agent

        # Log model and tool information
        logger.info(f"Agent model: {pydantic_agent.model}")
        tool_names = _get_agent_tool_names(pydantic_agent)
        logger.info(f"Agent tools available: {tool_names}")

        # Start performance timing if enabled
        collector = self._perf_collectors.get(session_id)
        if collector:
            logger.info("Starting performance timing")
            # Determine backend - always "ide" for ACP mode
            backend = "ide"
            collector.start_prompt(str(self._model), backend)

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

        # End performance timing and generate report if enabled
        if collector:
            logger.info("Ending performance timing and generating report")
            collector.end_prompt()
            try:
                report_data = collector.report()
                html = generate_html_report(report_data)

                # Generate filename with timestamp
                timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
                report_filename = f"punie-perf-{timestamp}.html"

                # Save to current working directory (should be workspace root)
                report_path = Path.cwd() / report_filename
                report_path.write_text(html)
                logger.info(f"Performance report saved to: {report_path}")

                # Append report location to response
                response_text += f"\n\n📊 **Performance report**: `{report_filename}`"
            except Exception as perf_exc:
                logger.warning(f"Failed to generate performance report: {perf_exc}")

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
