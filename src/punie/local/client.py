"""Local client implementation using real filesystem and subprocess operations."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from punie.acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    AgentThoughtChunk,
    AllowedOutcome,
    AvailableCommandsUpdate,
    ConfigOptionUpdate,
    CreateTerminalResponse,
    CurrentModeUpdate,
    EnvVariable,
    KillTerminalCommandResponse,
    PermissionOption,
    ReadTextFileResponse,
    ReleaseTerminalResponse,
    RequestPermissionResponse,
    SessionInfoUpdate,
    TerminalOutputResponse,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
    UserMessageChunk,
    WaitForTerminalExitResponse,
    WriteTextFileResponse,
)

__all__ = ["LocalClient"]


@dataclass
class LocalClient:
    """Client protocol implementation using local filesystem and subprocess.

    Implements the same Client protocol as ACP client but uses real filesystem
    operations via pathlib.Path and subprocess via asyncio.subprocess instead
    of delegating to IDE via JSON-RPC.

    Args:
        workspace: Root directory for file operations
    """

    workspace: Path
    _terminals: dict[str, asyncio.subprocess.Process] = field(
        default_factory=dict, init=False
    )
    _terminal_outputs: dict[str, str] = field(default_factory=dict, init=False)
    _agent: Any | None = field(default=None, init=False)

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to workspace.

        Args:
            path: File path (absolute or relative to workspace)

        Returns:
            Resolved absolute path
        """
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        return self.workspace / path_obj

    async def read_text_file(
        self,
        path: str,
        session_id: str,
        limit: int | None = None,
        line: int | None = None,
        **kwargs: Any,
    ) -> ReadTextFileResponse:
        """Read file from local filesystem.

        Args:
            path: File path to read
            session_id: Session ID (unused in local mode)
            limit: Maximum number of lines to read
            line: Starting line number (1-indexed)
            **kwargs: Additional parameters (unused)

        Returns:
            ReadTextFileResponse with file content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self._resolve_path(path)
        content = full_path.read_text()

        # Handle line/limit parameters
        if line is not None or limit is not None:
            lines = content.splitlines(keepends=True)
            start = (line - 1) if line else 0
            end = start + limit if limit else None
            content = "".join(lines[start:end])

        return ReadTextFileResponse(content=content)

    async def write_text_file(
        self, content: str, path: str, session_id: str, **kwargs: Any
    ) -> WriteTextFileResponse | None:
        """Write file to local filesystem.

        Args:
            content: File content to write
            path: File path to write to
            session_id: Session ID (unused in local mode)
            **kwargs: Additional parameters (unused)

        Returns:
            WriteTextFileResponse on success
        """
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return WriteTextFileResponse()

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCallUpdate,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        """Auto-approve permission requests.

        Since there's no IDE to prompt the user, auto-approve by selecting
        the first option.

        Args:
            options: Permission options to choose from
            session_id: Session ID (unused in local mode)
            tool_call: Tool call requesting permission
            **kwargs: Additional parameters (unused)

        Returns:
            RequestPermissionResponse with first option selected
        """
        if not options:
            return RequestPermissionResponse(
                outcome=AllowedOutcome(option_id="", outcome="selected")
            )
        return RequestPermissionResponse(
            outcome=AllowedOutcome(option_id=options[0].option_id, outcome="selected")
        )

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
        """No-op: no IDE to receive notifications.

        ToolCallTracker still runs and calls this method, but notifications
        go nowhere in local mode since there's no IDE to receive them.

        Args:
            session_id: Session ID
            update: Session update notification
            **kwargs: Additional parameters (unused)
        """
        pass

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
        """Create subprocess for command execution.

        Args:
            command: Command to execute
            session_id: Session ID (unused in local mode)
            args: Command arguments
            cwd: Working directory for command
            env: Environment variables
            output_byte_limit: Maximum output bytes (unused)
            **kwargs: Additional parameters (unused)

        Returns:
            CreateTerminalResponse with terminal_id
        """
        # Build command line
        cmd_args = [command] + (args or [])

        # Build environment dict
        env_dict = None
        if env:
            env_dict = {var.name: var.value for var in env}

        # Resolve working directory
        work_dir = self._resolve_path(cwd) if cwd else self.workspace

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(work_dir),
            env=env_dict,
        )

        # Generate terminal ID and store process
        terminal_id = f"term-{id(process)}"
        self._terminals[terminal_id] = process
        self._terminal_outputs[terminal_id] = ""

        return CreateTerminalResponse(terminal_id=terminal_id)

    async def terminal_output(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> TerminalOutputResponse:
        """Get output from subprocess.

        Args:
            session_id: Session ID (unused in local mode)
            terminal_id: Terminal ID from create_terminal
            **kwargs: Additional parameters (unused)

        Returns:
            TerminalOutputResponse with output content

        Raises:
            KeyError: If terminal_id not found
        """
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")

        process = self._terminals[terminal_id]

        # Read available output without blocking
        if process.stdout:
            try:
                # Try to read available data
                data = await asyncio.wait_for(
                    process.stdout.read(8192), timeout=0.1
                )
                if data:
                    output = data.decode("utf-8", errors="replace")
                    self._terminal_outputs[terminal_id] += output
            except asyncio.TimeoutError:
                pass

        return TerminalOutputResponse(
            output=self._terminal_outputs[terminal_id], truncated=False
        )

    async def release_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> ReleaseTerminalResponse | None:
        """Clean up terminal resources.

        Args:
            session_id: Session ID (unused in local mode)
            terminal_id: Terminal ID from create_terminal
            **kwargs: Additional parameters (unused)

        Returns:
            ReleaseTerminalResponse on success
        """
        if terminal_id in self._terminals:
            del self._terminals[terminal_id]
        if terminal_id in self._terminal_outputs:
            del self._terminal_outputs[terminal_id]
        return ReleaseTerminalResponse()

    async def wait_for_terminal_exit(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> WaitForTerminalExitResponse:
        """Wait for subprocess to complete.

        Args:
            session_id: Session ID (unused in local mode)
            terminal_id: Terminal ID from create_terminal
            **kwargs: Additional parameters (unused)

        Returns:
            WaitForTerminalExitResponse with exit code

        Raises:
            KeyError: If terminal_id not found
        """
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")

        process = self._terminals[terminal_id]

        # Read any remaining output before waiting
        if process.stdout:
            remaining = await process.stdout.read()
            if remaining:
                output = remaining.decode("utf-8", errors="replace")
                self._terminal_outputs[terminal_id] += output

        # Wait for process to complete
        exit_code = await process.wait()

        return WaitForTerminalExitResponse(exit_code=exit_code)

    async def kill_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> KillTerminalCommandResponse | None:
        """Kill subprocess.

        Args:
            session_id: Session ID (unused in local mode)
            terminal_id: Terminal ID from create_terminal
            **kwargs: Additional parameters (unused)

        Returns:
            KillTerminalCommandResponse on success

        Raises:
            KeyError: If terminal_id not found
        """
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")

        process = self._terminals[terminal_id]
        process.kill()
        await process.wait()

        # Clean up
        del self._terminals[terminal_id]
        if terminal_id in self._terminal_outputs:
            del self._terminal_outputs[terminal_id]

        return KillTerminalCommandResponse()

    async def discover_tools(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        """Return empty tool catalog (no IDE discovery in local mode).

        Args:
            session_id: Session ID (unused in local mode)
            **kwargs: Additional parameters (unused)

        Returns:
            Empty tool catalog
        """
        return {"tools": []}

    async def ext_method(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Raise error for extension methods (not supported in local mode).

        Args:
            method: Extension method name
            params: Method parameters

        Raises:
            NotImplementedError: Extension methods not supported locally
        """
        raise NotImplementedError(
            f"Extension method {method} not supported in local mode"
        )

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        """No-op for extension notifications.

        Args:
            method: Extension notification name
            params: Notification parameters
        """
        pass

    def on_connect(self, conn: Any) -> None:
        """Store agent reference on connection.

        Args:
            conn: Agent connection
        """
        self._agent = conn
