"""Pydantic AI toolset that bridges to ACP Client Protocol.

Exposes ACP Client methods as Pydantic AI tools: read_file, write_file (with
permission), run_command (with permission), and terminal lifecycle tools.

Provides three toolset factories:
- create_toolset() — All 7 static tools (backward compat, Tier 3 fallback)
- create_toolset_from_capabilities() — Build from ClientCapabilities (Tier 2 fallback)
- create_toolset_from_catalog() — Build from ToolCatalog (Tier 1, dynamic discovery)
"""

import logging
from typing import Any

from pydantic_ai import FunctionToolset, ModelRetry, RunContext
from punie.acp.contrib.permissions import default_permission_options
from punie.acp.helpers import text_block, tool_content, tool_terminal_ref
from punie.acp.schema import ClientCapabilities, ToolCallLocation
from punie.agent.deps import ACPDeps
from punie.agent.discovery import ToolCatalog, ToolDescriptor

logger = logging.getLogger(__name__)


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
    logger.info(f"🔧 TOOL: read_file(path={path})")

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
        logger.debug(f"Calling client_conn.read_text_file({path})")
        response = await ctx.deps.client_conn.read_text_file(
            session_id=ctx.deps.session_id,
            path=path,
        )
        logger.info(f"✓ Read {len(response.content)} chars from {path}")

        # Report completion
        progress = ctx.deps.tracker.progress(
            tool_call_id,
            status="completed",
            content=[tool_content(text_block(response.content))],
        )
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)

        return response.content
    except Exception as exc:
        logger.error(f"✗ Failed to read {path}: {exc}")
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
    logger.info(f"🔧 TOOL: write_file(path={path}, content={len(content)} chars)")
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

    Accepts either:
    1. Separate command and args: command="grep", args=["-r", "pattern", "."]
    2. Full command string: command="grep -r pattern ." (auto-split)

    Args:
        ctx: Run context with ACPDeps
        command: Command to execute (or full command string to auto-split)
        args: Optional command arguments (ignored if command contains spaces)
        cwd: Optional working directory

    Returns:
        Command output or denial message
    """
    import shlex

    # Auto-split if command contains spaces and no args provided
    # This handles models that pass full command strings
    if args is None and ' ' in command:
        try:
            parts = shlex.split(command)
            if len(parts) > 1:
                command = parts[0]
                args = parts[1:]
        except ValueError:
            # shlex.split failed (unclosed quotes, etc.) - use as-is
            pass

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


async def execute_code(ctx: RunContext[ACPDeps], code: str) -> str:
    """Execute Python code with multiple tool calls (Code Mode).

    Runs model-generated Python code in a restricted sandbox. The code can call
    read_file, write_file, and run_command to perform multi-step operations in
    a single turn.

    Reports tool call lifecycle to IDE via session_update.

    NOTE: Current implementation is for training validation with fake external
    functions. Production integration requires proper async bridge pattern
    (either Monty's external call pattern or thread pool executor).

    Args:
        ctx: Run context with ACPDeps
        code: Python source code to execute

    Returns:
        Captured stdout from code execution

    Example:
        code = '''
        files = run_command("find", args=["-name", "*.py"]).splitlines()
        total = sum(read_file(f).count("import ") for f in files)
        print(f"Found {total} imports")
        '''
    """
    from punie.agent.monty_runner import (
        CodeExecutionError,
        ExternalFunctions,
        run_code,
    )

    logger.info(f"🔧 TOOL: execute_code({len(code)} chars)")
    tool_call_id = "execute_code"

    # Start tracking
    start = ctx.deps.tracker.start(
        tool_call_id, title="Executing Python code", kind="execute"
    )
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)

    try:
        # Create async-to-sync bridge for external functions
        # The sandbox runs synchronously (exec is inherently sync), but external
        # functions need to call async ACP tools. We use run_coroutine_threadsafe
        # to bridge from the sync sandbox back to the async event loop.
        import asyncio

        loop = asyncio.get_running_loop()

        def sync_read_file(path: str) -> str:
            """Bridge from sync sandbox to async read_text_file ACP tool."""
            future = asyncio.run_coroutine_threadsafe(
                ctx.deps.client_conn.read_text_file(
                    session_id=ctx.deps.session_id, path=path
                ),
                loop,
            )
            response = future.result(timeout=30)
            return response.content

        def sync_write_file(path: str, content: str) -> str:
            """Bridge from sync sandbox to async write_text_file ACP tool."""
            future = asyncio.run_coroutine_threadsafe(
                ctx.deps.client_conn.write_text_file(
                    session_id=ctx.deps.session_id, path=path, content=content
                ),
                loop,
            )
            response = future.result(timeout=30)
            return "success"  # write_text_file returns None, return success marker

        def sync_run_command(
            command: str, args: list[str] | None = None, cwd: str | None = None
        ) -> str:
            """Bridge from sync sandbox to async terminal workflow (create/wait/output/release)."""
            # Use terminal workflow: create -> wait -> get output -> release
            async def _run_terminal():
                term = await ctx.deps.client_conn.create_terminal(
                    command=command,
                    args=args or [],
                    cwd=cwd,
                    session_id=ctx.deps.session_id,
                )
                await ctx.deps.client_conn.wait_for_terminal_exit(
                    session_id=ctx.deps.session_id, terminal_id=term.terminal_id
                )
                output_resp = await ctx.deps.client_conn.terminal_output(
                    session_id=ctx.deps.session_id, terminal_id=term.terminal_id
                )
                await ctx.deps.client_conn.release_terminal(
                    session_id=ctx.deps.session_id, terminal_id=term.terminal_id
                )
                return output_resp.output

            future = asyncio.run_coroutine_threadsafe(_run_terminal(), loop)
            return future.result(timeout=30)

        def sync_typecheck(path: str):  # type: ignore[no-untyped-def]
            """Bridge from sync sandbox to async ty type checker via terminal."""
            from punie.agent.typed_tools import TypeCheckResult, parse_ty_output

            # Use terminal workflow to run ty check with JSON output
            async def _run_typecheck() -> TypeCheckResult:
                term = await ctx.deps.client_conn.create_terminal(
                    command="ty",
                    args=["check", path, "--output-format", "json"],
                    cwd=None,
                    session_id=ctx.deps.session_id,
                )
                await ctx.deps.client_conn.wait_for_terminal_exit(
                    session_id=ctx.deps.session_id, terminal_id=term.terminal_id
                )
                output_resp = await ctx.deps.client_conn.terminal_output(
                    session_id=ctx.deps.session_id, terminal_id=term.terminal_id
                )
                await ctx.deps.client_conn.release_terminal(
                    session_id=ctx.deps.session_id, terminal_id=term.terminal_id
                )
                # Parse JSON output into TypeCheckResult
                return parse_ty_output(output_resp.output)

            future = asyncio.run_coroutine_threadsafe(_run_typecheck(), loop)
            return future.result(timeout=30)

        # Execute code in sandbox (runs in thread pool to not block event loop)
        external_functions = ExternalFunctions(
            read_file=sync_read_file,
            write_file=sync_write_file,
            run_command=sync_run_command,
            typecheck=sync_typecheck,
        )
        output = await loop.run_in_executor(None, run_code, code, external_functions)

        # Report completion
        progress = ctx.deps.tracker.progress(
            tool_call_id,
            status="completed",
            content=[tool_content(text_block(output))],
        )
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)

        return output
    except CodeExecutionError as exc:
        logger.error(f"✗ Code execution failed: {exc}")
        raise ModelRetry(f"Code execution failed: {exc}") from exc
    except Exception as exc:
        logger.error(f"✗ Unexpected error: {exc}")
        raise ModelRetry(f"Failed to execute code: {exc}") from exc
    finally:
        # Clean up tracker
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
    """Create ACP toolset with all client tools (Tier 3 fallback).

    Returns a FunctionToolset configured with tools that bridge Pydantic AI
    to ACP Client Protocol:
    - read_file
    - write_file (with permission)
    - run_command (with permission)
    - execute_code (Code Mode for multi-step operations)
    - get_terminal_output
    - release_terminal
    - wait_for_terminal_exit
    - kill_terminal

    This is the backward-compatible "all tools" factory, used when:
    - No client capabilities provided (old clients)
    - No tool catalog available (discovery not supported)
    """
    return FunctionToolset[ACPDeps](
        tools=[
            read_file,
            write_file,
            run_command,
            execute_code,
            get_terminal_output,
            release_terminal,
            wait_for_terminal_exit,
            kill_terminal,
        ]
    )


def create_toolset_from_capabilities(
    caps: ClientCapabilities,
) -> FunctionToolset[ACPDeps]:
    """Create toolset from client capabilities (Tier 2 fallback).

    Builds a toolset based on what the client declares it can do via
    ClientCapabilities. Only includes tools the client supports.

    Args:
        caps: Client capabilities from initialize()

    Returns:
        FunctionToolset with capability-filtered tools

    >>> from punie.acp.schema import ClientCapabilities, FileSystemCapability
    >>> caps = ClientCapabilities(
    ...     fs=FileSystemCapability(read_text_file=True, write_text_file=False),
    ...     terminal=False
    ... )
    >>> toolset = create_toolset_from_capabilities(caps)
    >>> len(toolset.tools)
    1
    """
    tools = []

    # File tools based on fs capability
    if caps.fs and caps.fs.read_text_file:
        tools.append(read_file)
    if caps.fs and caps.fs.write_text_file:
        tools.append(write_file)

    # Terminal tools if terminal capability enabled
    if caps.terminal:
        tools.extend(
            [
                run_command,
                get_terminal_output,
                release_terminal,
                wait_for_terminal_exit,
                kill_terminal,
            ]
        )

    return FunctionToolset[ACPDeps](tools=tools)


def _create_generic_bridge(descriptor: ToolDescriptor):
    """Create a generic bridge function for unknown IDE tools.

    For tools not in the known set (read_file, write_file, etc.), generate
    a dynamic bridge that forwards calls to ext_method.

    Args:
        descriptor: Tool descriptor from IDE

    Returns:
        Async function matching Pydantic AI tool signature
    """

    async def bridge(ctx: RunContext[ACPDeps], **kwargs: Any) -> Any:
        """Generic bridge to IDE tool via ext_method."""
        conn = ctx.deps.client_conn
        try:
            return await conn.ext_method(
                descriptor.name, params={"session_id": ctx.deps.session_id, **kwargs}
            )
        except Exception as exc:
            raise ModelRetry(f"Failed to call {descriptor.name}: {exc}") from exc

    # Set function metadata for Pydantic AI
    bridge.__name__ = descriptor.name
    bridge.__doc__ = descriptor.description
    return bridge


def create_toolset_from_catalog(catalog: ToolCatalog) -> FunctionToolset[ACPDeps]:
    """Create toolset from tool catalog (Tier 1, dynamic discovery).

    Builds a toolset from the IDE's advertised capabilities via discover_tools().
    Matches known tools by name, creates generic bridges for unknowns.

    Args:
        catalog: Tool catalog from discover_tools() response

    Returns:
        FunctionToolset with catalog-matched tools

    >>> from punie.agent.discovery import ToolDescriptor, ToolCatalog
    >>> descriptor = ToolDescriptor(
    ...     name="read_file",
    ...     kind="read",
    ...     description="Read file",
    ...     parameters={"type": "object"}
    ... )
    >>> catalog = ToolCatalog(tools=(descriptor,))
    >>> toolset = create_toolset_from_catalog(catalog)
    >>> len(toolset.tools)
    1
    """
    # Known tools mapping
    known_tools = {
        "read_file": read_file,
        "write_file": write_file,
        "run_command": run_command,
        "get_terminal_output": get_terminal_output,
        "release_terminal": release_terminal,
        "wait_for_terminal_exit": wait_for_terminal_exit,
        "kill_terminal": kill_terminal,
    }

    tools = []
    for descriptor in catalog.tools:
        if descriptor.name in known_tools:
            # Use known implementation
            tools.append(known_tools[descriptor.name])
        else:
            # Create generic bridge for IDE-provided tool
            tools.append(_create_generic_bridge(descriptor))

    return FunctionToolset[ACPDeps](tools=tools)


# Alias for backward compatibility
ACPToolset = create_toolset
