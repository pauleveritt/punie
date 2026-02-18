"""Fake ACP protocol implementations for testing.

Provides FakeAgent and FakeClient with configurable behavior.
"""

from dataclasses import dataclass, field
from typing import Any

from punie.acp import (
    AuthenticateResponse,
    CreateTerminalResponse,
    InitializeResponse,
    KillTerminalCommandResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    ReadTextFileResponse,
    ReleaseTerminalResponse,
    RequestError,
    RequestPermissionResponse,
    SessionNotification,
    SetSessionModeResponse,
    TerminalOutputResponse,
    WaitForTerminalExitResponse,
    WriteTextFileResponse,
)
from punie.acp.schema import (
    ForkSessionResponse,
    ListSessionsResponse,
    ResumeSessionResponse,
    SetSessionModelResponse,
)
from punie.acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    AgentThoughtChunk,
    AllowedOutcome,
    AudioContentBlock,
    AvailableCommandsUpdate,
    ClientCapabilities,
    ConfigOptionUpdate,
    CurrentModeUpdate,
    DeniedOutcome,
    EmbeddedResourceContentBlock,
    EnvVariable,
    HttpMcpServer,
    ImageContentBlock,
    Implementation,
    McpServerStdio,
    PermissionOption,
    ResourceContentBlock,
    SessionInfoUpdate,
    SseMcpServer,
    TextContentBlock,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
    UserMessageChunk,
)

__all__ = ["FakeAgent", "FakeClient", "FakeTerminal", "FakeWebSocket"]


@dataclass
class FakeTerminal:
    """In-memory terminal state for testing.

    Args:
        command: The command that was run
        args: Command arguments
        output: Terminal output content
        exit_code: Exit code from command execution
    """

    command: str
    args: list[str] = field(default_factory=list)
    output: str = ""
    exit_code: int = 0


class FakeClient:
    """Fake client implementation for testing Agent Protocol calls.

    Provides in-memory implementations of Client Protocol methods:
    - File operations use `files` dict
    - Permission prompts use `permission_outcomes` queue
    - Notifications are recorded in `notifications` list
    - Tool discovery via `tool_catalog` (dynamic discovery)
    - Client capabilities via `capabilities` (capability-based fallback)
    - Discovery call tracking via `discover_tools_calls` (session registration tests)

    Args:
        files: Initial file system state (path -> content mapping)
        default_file_content: Content returned for files not in `files` dict
        tool_catalog: List of tool descriptor dicts for discover_tools()
        capabilities: Client capabilities for capability-based fallback
    """

    __test__ = False  # Prevent pytest collection

    def __init__(
        self,
        files: dict[str, str] | None = None,
        default_file_content: str = "default content",
        tool_catalog: list[dict[str, Any]] | None = None,
        capabilities: ClientCapabilities | None = None,
    ) -> None:
        self.files: dict[str, str] = files or {}
        self.default_file_content = default_file_content
        self.permission_outcomes: list[RequestPermissionResponse] = []
        self.notifications: list[SessionNotification] = []
        self.ext_calls: list[tuple[str, dict]] = []
        self.ext_notes: list[tuple[str, dict]] = []
        self._agent_conn = None
        self.terminals: dict[str, FakeTerminal] = {}
        self._next_terminal_id: int = 0
        self.tool_catalog = tool_catalog or []
        self.capabilities = capabilities
        self.discover_tools_calls: list[str] = []

    def on_connect(self, conn) -> None:
        self._agent_conn = conn

    def queue_permission_cancelled(self) -> None:
        self.permission_outcomes.append(
            RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))
        )

    def queue_permission_selected(self, option_id: str) -> None:
        self.permission_outcomes.append(
            RequestPermissionResponse(
                outcome=AllowedOutcome(option_id=option_id, outcome="selected")
            )
        )

    def queue_terminal(
        self,
        command: str,
        output: str = "",
        exit_code: int = 0,
        args: list[str] | None = None,
    ) -> str:
        """Pre-configure a terminal for testing.

        Args:
            command: Command to match on create_terminal()
            output: Output to return from terminal_output()
            exit_code: Exit code to return from wait_for_terminal_exit()
            args: Command arguments to match

        Returns:
            Terminal ID that will be assigned
        """
        terminal_id = f"term-{self._next_terminal_id}"
        self._next_terminal_id += 1
        self.terminals[terminal_id] = FakeTerminal(
            command=command, args=args or [], output=output, exit_code=exit_code
        )
        return terminal_id

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCallUpdate,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        if self.permission_outcomes:
            return self.permission_outcomes.pop()
        return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))

    async def write_text_file(
        self, content: str, path: str, session_id: str, **kwargs: Any
    ) -> WriteTextFileResponse | None:
        self.files[str(path)] = content
        return WriteTextFileResponse()

    async def read_text_file(
        self,
        path: str,
        session_id: str,
        limit: int | None = None,
        line: int | None = None,
        **kwargs: Any,
    ) -> ReadTextFileResponse:
        content = self.files.get(str(path), self.default_file_content)
        return ReadTextFileResponse(content=content)

    async def session_update(
        self,
        session_id: str,
        update: UserMessageChunk
        | AgentMessageChunk
        | AgentThoughtChunk
        | ToolCallStart
        | ToolCallProgress
        | AgentPlanUpdate
        | AvailableCommandsUpdate
        | CurrentModeUpdate
        | ConfigOptionUpdate
        | SessionInfoUpdate,
        **kwargs: Any,
    ) -> None:
        self.notifications.append(
            SessionNotification(
                session_id=session_id, update=update, field_meta=kwargs or None
            )
        )

    # Terminal methods with in-memory implementation
    async def create_terminal(
        self,
        command: str,
        session_id: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: list[EnvVariable] | None = None,
        output_byte_limit: int | None = None,
        **kwargs: Any,
    ) -> CreateTerminalResponse:
        terminal_id = f"term-{self._next_terminal_id}"
        self._next_terminal_id += 1

        # If terminal was pre-configured via queue_terminal(), use it
        # Otherwise create a default terminal
        if terminal_id not in self.terminals:
            self.terminals[terminal_id] = FakeTerminal(
                command=command, args=args or [], output="", exit_code=0
            )

        return CreateTerminalResponse(terminal_id=terminal_id)

    async def terminal_output(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> TerminalOutputResponse:
        if terminal_id is None or terminal_id not in self.terminals:
            return TerminalOutputResponse(output="", truncated=False)
        return TerminalOutputResponse(
            output=self.terminals[terminal_id].output, truncated=False
        )

    async def release_terminal(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> ReleaseTerminalResponse | None:
        if terminal_id and terminal_id in self.terminals:
            del self.terminals[terminal_id]
        return ReleaseTerminalResponse()

    async def wait_for_terminal_exit(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> WaitForTerminalExitResponse:
        if terminal_id is None or terminal_id not in self.terminals:
            return WaitForTerminalExitResponse(exit_code=0)
        return WaitForTerminalExitResponse(
            exit_code=self.terminals[terminal_id].exit_code
        )

    async def kill_terminal(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> KillTerminalCommandResponse | None:
        if terminal_id and terminal_id in self.terminals:
            del self.terminals[terminal_id]
        return KillTerminalCommandResponse()

    async def discover_tools(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        """Return configured tool catalog for dynamic discovery.

        Returns the tool_catalog set at construction time. Used to test
        dynamic tool discovery (Tier 1 fallback).

        Tracks session_id in discover_tools_calls for session registration tests.
        """
        self.discover_tools_calls.append(session_id)
        return {"tools": self.tool_catalog}

    async def ext_method(self, method: str, params: dict) -> dict:
        self.ext_calls.append((method, params))
        if method == "example.com/ping":
            return {"response": "pong", "params": params}
        raise RequestError.method_not_found(method)

    async def ext_notification(self, method: str, params: dict) -> None:
        self.ext_notes.append((method, params))


class FakeAgent:
    """Fake agent implementation for testing Client Protocol calls.

    Provides minimal implementations of Agent Protocol methods:
    - initialize echoes protocol version
    - new_session returns fixed session ID
    - prompt records requests and returns end_turn
    - cancel records session IDs

    Args:
        session_id: Session ID returned by new_session() (default: "test-session-123")
        protocol_version: Protocol version returned by initialize() (echoes request by default)
    """

    __test__ = False  # Prevent pytest collection

    def __init__(
        self,
        session_id: str = "test-session-123",
        protocol_version: int | None = None,
    ) -> None:
        self.session_id = session_id
        self._protocol_version = protocol_version
        self.prompts: list[PromptRequest] = []
        self.cancellations: list[str] = []
        self.ext_calls: list[tuple[str, dict]] = []
        self.ext_notes: list[tuple[str, dict]] = []

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        # Use configured version or echo request
        version = (
            self._protocol_version
            if self._protocol_version is not None
            else protocol_version
        )
        return InitializeResponse(
            protocol_version=version, agent_capabilities=None, auth_methods=[]
        )

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        **kwargs: Any,
    ) -> NewSessionResponse:
        return NewSessionResponse(session_id=self.session_id)

    async def load_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        session_id: str,
        **kwargs: Any,
    ) -> LoadSessionResponse | None:
        return LoadSessionResponse()

    async def authenticate(
        self, method_id: str, **kwargs: Any
    ) -> AuthenticateResponse | None:
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
        self.prompts.append(
            PromptRequest(
                prompt=prompt, session_id=session_id, field_meta=kwargs or None
            )
        )
        return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        self.cancellations.append(session_id)

    async def list_sessions(
        self, cursor: str | None = None, cwd: str | None = None, **kwargs: Any
    ) -> ListSessionsResponse:
        return ListSessionsResponse(sessions=[], next_cursor=None)

    async def set_session_mode(
        self, mode_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModeResponse | None:
        return SetSessionModeResponse()

    async def set_session_model(
        self, model_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModelResponse | None:
        return SetSessionModelResponse()

    async def fork_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> ForkSessionResponse:
        return ForkSessionResponse(session_id=f"{session_id}-fork")

    async def resume_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> ResumeSessionResponse:
        return ResumeSessionResponse()

    async def ext_method(self, method: str, params: dict) -> dict:
        self.ext_calls.append((method, params))
        if method == "example.com/echo":
            return {"echo": params}
        raise RequestError.method_not_found(method)

    async def ext_notification(self, method: str, params: dict) -> None:
        self.ext_notes.append((method, params))

    def on_connect(self, conn) -> None:
        """Called when client connection is established."""
        pass


class FakeWebSocket:
    """Fake WebSocket for testing client-side receive loops.

    Simulates the websockets ClientConnection interface with pre-configured
    response sequences.

    Args:
        responses: List of message dicts to return from recv().
                   Each dict is JSON-serialized. Pass
                   ``{"__close__": True}`` to simulate connection close.
        close_after: If set, raises ConnectionClosed after this many recv() calls.

    Example:
        fake = FakeWebSocket(responses=[
            {"method": "session_update", "params": {"update": {"sessionUpdate": "agent_message_chunk"}}},
            {"id": "req-1", "result": {"status": "ok"}},
        ])
        result = await receive_messages(fake, request_id="req-1")
        assert result == {"status": "ok"}
        assert fake.sent  # verify we sent the prompt
    """

    __test__ = False

    def __init__(
        self,
        responses: list[dict] | None = None,
        close_after: int | None = None,
    ) -> None:
        import json as _json
        self._json = _json
        self._responses = list(responses or [])
        self._close_after = close_after
        self._recv_count = 0
        self.sent: list[str] = []  # messages sent via send()

    async def send(self, data: str | bytes) -> None:
        """Record sent data."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        self.sent.append(data)

    async def recv(self) -> str:
        """Return next pre-configured response or raise ConnectionClosed."""
        import websockets.exceptions

        self._recv_count += 1

        if self._close_after is not None and self._recv_count > self._close_after:
            raise websockets.exceptions.ConnectionClosed(None, None)  # type: ignore[arg-type]

        if not self._responses:
            raise websockets.exceptions.ConnectionClosed(None, None)  # type: ignore[arg-type]

        response = self._responses.pop(0)

        # Special sentinel: simulate connection close
        if response.get("__close__"):
            raise websockets.exceptions.ConnectionClosed(None, None)  # type: ignore[arg-type]

        return self._json.dumps(response)

    async def close(self) -> None:
        """Simulate connection close."""
        pass
