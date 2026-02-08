"""Pydantic AI toolset that bridges to ACP Client Protocol.

Exposes ACP Client methods as Pydantic AI tools: read_file, write_file (with
permission), run_command (with permission), and terminal lifecycle tools.
"""

from pydantic_ai import FunctionToolset, ModelRetry, RunContext

from punie.acp.contrib.permissions import default_permission_options
from punie.acp.helpers import text_block, tool_content, tool_terminal_ref
from punie.acp.schema import ToolCallLocation

from .deps import ACPDeps


async def read_file(ctx: RunContext[ACPDeps], path: str) -> str:
    """Read contents of a text file from the IDE workspace.

    Reports tool call lifecycle to IDE via session_update:
    1. Send ToolCallStart when beginning
    2. Call client_conn.read_text_file()
    3. Send ToolCallProgress when complete

    Args:
        ctx: Run context with ACPDeps
        path: Absolute or workspace-relative file path

    Returns:
        File contents as string
    """
    # Start tracking this tool call
    tool_call_id = f"read_{path}"
    start = ctx.deps.tracker.start(
        tool_call_id,
        title=f"Reading {path}",
        kind="read",
        locations=[ToolCallLocation(path=path)],
    )
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)

    try:
        # Perform ACP file read
        response = await ctx.deps.client_conn.read_text_file(
            session_id=ctx.deps.session_id,
            path=path,
        )

        # Report completion
        progress = ctx.deps.tracker.progress(
            tool_call_id,
            status="completed",
            content=[tool_content(text_block(response.content))],
        )
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)

        return response.content
    except Exception as exc:
        raise ModelRetry(f"Failed to read {path}: {exc}") from exc
    finally:
        # Clean up tracker
        ctx.deps.tracker.forget(tool_call_id)


async def write_file(ctx: RunContext[ACPDeps], path: str, content: str) -> str:
    """Write contents to a text file in the IDE workspace.

    Requests user permission before writing. Reports tool call lifecycle to IDE.

    Args:
        ctx: Run context with ACPDeps
        path: Absolute or workspace-relative file path
        content: Text content to write

    Returns:
        Success or denial message
    """
    tool_call_id = f"write_{path}"

    # Start tracking
    start = ctx.deps.tracker.start(
        tool_call_id,
        title=f"Writing {path}",
        kind="edit",
        locations=[ToolCallLocation(path=path)],
    )
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)

    try:
        # Request permission
        perm_response = await ctx.deps.client_conn.request_permission(
            options=list(default_permission_options()),
            session_id=ctx.deps.session_id,
            tool_call=ctx.deps.tracker.tool_call_model(tool_call_id),
        )

        # Check outcome
        if perm_response.outcome.outcome != "selected":
            # Denied - return message (not an error, LLM should know)
            return f"Permission denied to write {path}"

        # Execute write
        await ctx.deps.client_conn.write_text_file(
            content=content, path=path, session_id=ctx.deps.session_id
        )

        # Report completion
        progress = ctx.deps.tracker.progress(
            tool_call_id,
            status="completed",
            content=[tool_content(text_block(f"Wrote {len(content)} chars to {path}"))],
        )
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)

        return f"Successfully wrote to {path}"
    except Exception as exc:
        raise ModelRetry(f"Failed to write {path}: {exc}") from exc
    finally:
        ctx.deps.tracker.forget(tool_call_id)


async def run_command(
    ctx: RunContext[ACPDeps],
    command: str,
    args: list[str] | None = None,
    cwd: str | None = None,
) -> str:
    """Run a shell command in the IDE terminal.

    Requests user permission before executing. Creates terminal, waits for
    completion, returns output.

    Args:
        ctx: Run context with ACPDeps
        command: Command to execute
        args: Optional command arguments
        cwd: Optional working directory

    Returns:
        Command output or denial message
    """
    tool_call_id = f"run_{command}"

    # Start tracking
    start = ctx.deps.tracker.start(
        tool_call_id, title=f"Running {command}", kind="execute"
    )
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)

    try:
        # Request permission
        perm_response = await ctx.deps.client_conn.request_permission(
            options=list(default_permission_options()),
            session_id=ctx.deps.session_id,
            tool_call=ctx.deps.tracker.tool_call_model(tool_call_id),
        )

        if perm_response.outcome.outcome != "selected":
            # Denied - return message (not an error, LLM should know)
            return f"Permission denied to run {command}"

        # Create terminal, wait for exit, get output
        term = await ctx.deps.client_conn.create_terminal(
            command=command, session_id=ctx.deps.session_id, args=args, cwd=cwd
        )
        await ctx.deps.client_conn.wait_for_terminal_exit(
            session_id=ctx.deps.session_id, terminal_id=term.terminal_id
        )
        output = await ctx.deps.client_conn.terminal_output(
            session_id=ctx.deps.session_id, terminal_id=term.terminal_id
        )
        await ctx.deps.client_conn.release_terminal(
            session_id=ctx.deps.session_id, terminal_id=term.terminal_id
        )

        # Report completion with terminal ref
        progress = ctx.deps.tracker.progress(
            tool_call_id,
            status="completed",
            content=[tool_terminal_ref(term.terminal_id)],
        )
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)

        return output.output
    except Exception as exc:
        raise ModelRetry(f"Failed to run command {command}: {exc}") from exc
    finally:
        ctx.deps.tracker.forget(tool_call_id)


async def get_terminal_output(ctx: RunContext[ACPDeps], terminal_id: str) -> str:
    """Get output from a terminal by ID.

    Args:
        ctx: Run context with ACPDeps
        terminal_id: Terminal identifier

    Returns:
        Terminal output text
    """
    try:
        response = await ctx.deps.client_conn.terminal_output(
            session_id=ctx.deps.session_id, terminal_id=terminal_id
        )
        return response.output
    except Exception as exc:
        raise ModelRetry(
            f"Failed to get output for terminal {terminal_id}: {exc}"
        ) from exc


async def release_terminal(ctx: RunContext[ACPDeps], terminal_id: str) -> str:
    """Release a terminal, freeing its resources.

    Args:
        ctx: Run context with ACPDeps
        terminal_id: Terminal identifier

    Returns:
        Confirmation message
    """
    try:
        await ctx.deps.client_conn.release_terminal(
            session_id=ctx.deps.session_id, terminal_id=terminal_id
        )
        return f"Released terminal {terminal_id}"
    except Exception as exc:
        raise ModelRetry(f"Failed to release terminal {terminal_id}: {exc}") from exc


async def wait_for_terminal_exit(ctx: RunContext[ACPDeps], terminal_id: str) -> str:
    """Wait for a terminal to exit and return its exit code.

    Args:
        ctx: Run context with ACPDeps
        terminal_id: Terminal identifier

    Returns:
        Exit code message
    """
    try:
        response = await ctx.deps.client_conn.wait_for_terminal_exit(
            session_id=ctx.deps.session_id, terminal_id=terminal_id
        )
        return f"Terminal exited with code {response.exit_code}"
    except Exception as exc:
        raise ModelRetry(f"Failed to wait for terminal {terminal_id}: {exc}") from exc


async def kill_terminal(ctx: RunContext[ACPDeps], terminal_id: str) -> str:
    """Kill a running terminal.

    Args:
        ctx: Run context with ACPDeps
        terminal_id: Terminal identifier

    Returns:
        Confirmation message
    """
    try:
        await ctx.deps.client_conn.kill_terminal(
            session_id=ctx.deps.session_id, terminal_id=terminal_id
        )
        return f"Killed terminal {terminal_id}"
    except Exception as exc:
        raise ModelRetry(f"Failed to kill terminal {terminal_id}: {exc}") from exc


def create_toolset() -> FunctionToolset[ACPDeps]:
    """Create ACP toolset with all client tools.

    Returns a FunctionToolset configured with tools that bridge Pydantic AI
    to ACP Client Protocol:
    - read_file
    - write_file (with permission)
    - run_command (with permission)
    - get_terminal_output
    - release_terminal
    - wait_for_terminal_exit
    - kill_terminal
    """
    return FunctionToolset[ACPDeps](
        tools=[
            read_file,
            write_file,
            run_command,
            get_terminal_output,
            release_terminal,
            wait_for_terminal_exit,
            kill_terminal,
        ]
    )


# Alias for backward compatibility
ACPToolset = create_toolset
