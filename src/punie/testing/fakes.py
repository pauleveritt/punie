"""Fake ACP protocol implementations for testing.

Provides FakeAgent and FakeClient with configurable behavior.
"""

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

__all__ = ["FakeAgent", "FakeClient"]


class FakeClient:
    """Fake client implementation for testing Agent Protocol calls.

    Provides in-memory implementations of Client Protocol methods:
    - File operations use `files` dict
    - Permission prompts use `permission_outcomes` queue
    - Notifications are recorded in `notifications` list

    Args:
        files: Initial file system state (path -> content mapping)
        default_file_content: Content returned for files not in `files` dict
    """

    __test__ = False  # Prevent pytest collection

    def __init__(
        self,
        files: dict[str, str] | None = None,
        default_file_content: str = "default content",
    ) -> None:
        self.files: dict[str, str] = files or {}
        self.default_file_content = default_file_content
        self.permission_outcomes: list[RequestPermissionResponse] = []
        self.notifications: list[SessionNotification] = []
        self.ext_calls: list[tuple[str, dict]] = []
        self.ext_notes: list[tuple[str, dict]] = []
        self._agent_conn = None

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

    # Optional terminal methods (not implemented in this test client)
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
        raise NotImplementedError

    async def terminal_output(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> TerminalOutputResponse:
        raise NotImplementedError

    async def release_terminal(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> ReleaseTerminalResponse | None:
        raise NotImplementedError

    async def wait_for_terminal_exit(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> WaitForTerminalExitResponse:
        raise NotImplementedError

    async def kill_terminal(
        self, session_id: str, terminal_id: str | None = None, **kwargs: Any
    ) -> KillTerminalCommandResponse | None:
        raise NotImplementedError

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
