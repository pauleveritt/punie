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
            future.result(timeout=30)
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

        def sync_typecheck(path: str):
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

        def sync_ruff_check(path: str):
            """Bridge from sync sandbox to async ruff linter via terminal."""
            from punie.agent.typed_tools import RuffResult, parse_ruff_output

            # Use terminal workflow to run ruff check
            async def _run_ruff() -> RuffResult:
                term = await ctx.deps.client_conn.create_terminal(
                    command="ruff",
                    args=["check", path],
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
                # Parse text output into RuffResult
                return parse_ruff_output(output_resp.output)

            future = asyncio.run_coroutine_threadsafe(_run_ruff(), loop)
            return future.result(timeout=30)

        def sync_goto_definition(file_path: str, line: int, column: int, symbol: str):
            """Bridge from sync sandbox to async LSP goto_definition."""
            from punie.agent.lsp_client import get_lsp_client
            from punie.agent.typed_tools import parse_definition_response

            # Use LSP client to query ty server
            async def _goto_definition():
                client = await get_lsp_client()
                response = await client.goto_definition(file_path, line, column)
                return parse_definition_response(response, symbol)

            future = asyncio.run_coroutine_threadsafe(_goto_definition(), loop)
            return future.result(timeout=30)

        def sync_find_references(file_path: str, line: int, column: int, symbol: str):
            """Bridge from sync sandbox to async LSP find_references."""
            from punie.agent.lsp_client import get_lsp_client
            from punie.agent.typed_tools import parse_references_response

            # Use LSP client to query ty server
            async def _find_references():
                client = await get_lsp_client()
                response = await client.find_references(file_path, line, column)
                return parse_references_response(response, symbol)

            future = asyncio.run_coroutine_threadsafe(_find_references(), loop)
            return future.result(timeout=30)

        def sync_pytest_run(path: str):
            """Bridge from sync sandbox to async pytest via terminal."""
            from punie.agent.typed_tools import TestResult, parse_pytest_output

            # Use terminal workflow to run pytest with verbose output
            async def _run_pytest() -> TestResult:
                term = await ctx.deps.client_conn.create_terminal(
                    command="pytest",
                    args=[path, "-v", "--tb=short"],
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
                # Parse verbose output into TestResult
                return parse_pytest_output(output_resp.output)

            future = asyncio.run_coroutine_threadsafe(_run_pytest(), loop)
            return future.result(timeout=30)

        def sync_hover(file_path: str, line: int, column: int, symbol: str):
            """Bridge from sync sandbox to async LSP hover."""
            from punie.agent.lsp_client import get_lsp_client
            from punie.agent.typed_tools import parse_hover_response

            # Use LSP client to query ty server
            async def _hover():
                client = await get_lsp_client()
                response = await client.hover(file_path, line, column)
                return parse_hover_response(response, symbol)

            future = asyncio.run_coroutine_threadsafe(_hover(), loop)
            return future.result(timeout=30)

        def sync_document_symbols(file_path: str):
            """Bridge from sync sandbox to async LSP document symbols."""
            from punie.agent.lsp_client import get_lsp_client
            from punie.agent.typed_tools import parse_document_symbols_response

            # Use LSP client to query ty server
            async def _document_symbols():
                client = await get_lsp_client()
                response = await client.document_symbols(file_path)
                return parse_document_symbols_response(response, file_path)

            future = asyncio.run_coroutine_threadsafe(_document_symbols(), loop)
            return future.result(timeout=30)

        def sync_workspace_symbols(query: str):
            """Bridge from sync sandbox to async LSP workspace symbols."""
            from punie.agent.lsp_client import get_lsp_client
            from punie.agent.typed_tools import parse_workspace_symbols_response

            # Use LSP client to query ty server
            async def _workspace_symbols():
                client = await get_lsp_client()
                response = await client.workspace_symbols(query)
                return parse_workspace_symbols_response(response, query)

            future = asyncio.run_coroutine_threadsafe(_workspace_symbols(), loop)
            return future.result(timeout=30)

        def sync_git_status(path: str):
            """Bridge from sync sandbox to async git status via terminal."""
            from punie.agent.typed_tools import GitStatusResult, parse_git_status_output

            # Use terminal workflow to run git status --porcelain
            async def _run_git_status() -> GitStatusResult:
                term = await ctx.deps.client_conn.create_terminal(
                    command="git",
                    args=["status", "--porcelain"],
                    cwd=path if path != "." else None,
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
                # Parse porcelain output into GitStatusResult
                return parse_git_status_output(output_resp.output)

            future = asyncio.run_coroutine_threadsafe(_run_git_status(), loop)
            return future.result(timeout=30)

        def sync_git_diff(path: str, staged: bool = False):
            """Bridge from sync sandbox to async git diff via terminal."""
            from punie.agent.typed_tools import GitDiffResult, parse_git_diff_output

            # Use terminal workflow to run git diff [--staged]
            async def _run_git_diff() -> GitDiffResult:
                args = ["diff"]
                if staged:
                    args.append("--staged")

                term = await ctx.deps.client_conn.create_terminal(
                    command="git",
                    args=args,
                    cwd=path if path != "." else None,
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
                # Parse diff output into GitDiffResult
                return parse_git_diff_output(output_resp.output)

            future = asyncio.run_coroutine_threadsafe(_run_git_diff(), loop)
            return future.result(timeout=30)

        def sync_git_log(path: str, count: int = 10):
            """Bridge from sync sandbox to async git log via terminal."""
            from punie.agent.typed_tools import GitLogResult, parse_git_log_output

            # Use terminal workflow to run git log with format including author/date
            async def _run_git_log() -> GitLogResult:
                term = await ctx.deps.client_conn.create_terminal(
                    command="git",
                    args=["log", "--format=%h|%an|%ad|%s", f"-n{count}"],
                    cwd=path if path != "." else None,
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
                # Parse formatted output into GitLogResult
                return parse_git_log_output(output_resp.output)

            future = asyncio.run_coroutine_threadsafe(_run_git_log(), loop)
            return future.result(timeout=30)

        def sync_cst_find_pattern(file_path: str, pattern: str):
            """Bridge from sync sandbox to local LibCST cst_find_pattern."""
            from punie.cst.code_tools import cst_find_pattern
            return cst_find_pattern(file_path, pattern)

        def sync_cst_rename(file_path: str, old_name: str, new_name: str):
            """Bridge from sync sandbox to local LibCST cst_rename."""
            from punie.cst.code_tools import cst_rename
            return cst_rename(file_path, old_name, new_name)

        def sync_cst_add_import(file_path: str, import_stmt: str):
            """Bridge from sync sandbox to local LibCST cst_add_import."""
            from punie.cst.code_tools import cst_add_import
            return cst_add_import(file_path, import_stmt)

        def sync_validate_component(file_path: str):
            """Bridge from sync sandbox to local LibCST validate_component."""
            from punie.cst.validators.tdom import validate_component
            return validate_component(file_path)

        def sync_check_render_tree(file_path: str):
            """Bridge from sync sandbox to local LibCST check_render_tree."""
            from punie.cst.validators.tdom import check_render_tree
            return check_render_tree(file_path)

        def sync_validate_escape_context(file_path: str):
            """Bridge from sync sandbox to local LibCST validate_escape_context."""
            from punie.cst.validators.tdom import validate_escape_context
            return validate_escape_context(file_path)

        def sync_validate_service_registration(file_path: str):
            """Bridge from sync sandbox to local LibCST validate_service_registration."""
            from punie.cst.validators.svcs import validate_service_registration
            return validate_service_registration(file_path)

        def sync_check_dependency_graph(file_path: str):
            """Bridge from sync sandbox to local LibCST check_dependency_graph."""
            from punie.cst.validators.svcs import check_dependency_graph
            return check_dependency_graph(file_path)

        def sync_validate_injection_site(file_path: str):
            """Bridge from sync sandbox to local LibCST validate_injection_site."""
            from punie.cst.validators.svcs import validate_injection_site
            return validate_injection_site(file_path)

        def sync_validate_middleware_chain(file_path: str):
            """Bridge from sync sandbox to local LibCST validate_middleware_chain."""
            from punie.cst.validators.tdom_svcs import validate_middleware_chain
            return validate_middleware_chain(file_path)

        def sync_check_di_template_binding(file_path: str):
            """Bridge from sync sandbox to local LibCST check_di_template_binding."""
            from punie.cst.validators.tdom_svcs import check_di_template_binding
            return check_di_template_binding(file_path)

        def sync_validate_route_pattern(file_path: str):
            """Bridge from sync sandbox to local LibCST validate_route_pattern."""
            from punie.cst.validators.tdom_svcs import validate_route_pattern
            return validate_route_pattern(file_path)

        # Execute code in sandbox (runs in thread pool to not block event loop)
        external_functions = ExternalFunctions(
            read_file=sync_read_file,
            write_file=sync_write_file,
            run_command=sync_run_command,
            typecheck=sync_typecheck,
            ruff_check=sync_ruff_check,
            pytest_run=sync_pytest_run,
            goto_definition=sync_goto_definition,
            find_references=sync_find_references,
            hover=sync_hover,
            document_symbols=sync_document_symbols,
            workspace_symbols=sync_workspace_symbols,
            git_status=sync_git_status,
            git_diff=sync_git_diff,
            git_log=sync_git_log,
            cst_find_pattern=sync_cst_find_pattern,
            cst_rename=sync_cst_rename,
            cst_add_import=sync_cst_add_import,
            validate_component=sync_validate_component,
            check_render_tree=sync_check_render_tree,
            validate_escape_context=sync_validate_escape_context,
            validate_service_registration=sync_validate_service_registration,
            check_dependency_graph=sync_check_dependency_graph,
            validate_injection_site=sync_validate_injection_site,
            validate_middleware_chain=sync_validate_middleware_chain,
            check_di_template_binding=sync_check_di_template_binding,
            validate_route_pattern=sync_validate_route_pattern,
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


# ============================================================================
# Direct Code Tools (Phase 38) - For zero-shot models like Devstral
# ============================================================================
# These tools bypass Code Mode indirection by exposing typed tools directly
# as PydanticAI tools. Used for models that weren't trained on Code Mode.


async def _run_terminal(
    ctx: RunContext[ACPDeps], command: str, args: list[str], cwd: str | None = None
) -> str:
    """Run a command via terminal and return output.

    Helper for direct Code Tools. Handles create → wait → output → release workflow.

    Args:
        ctx: Run context with ACPDeps
        command: Command to execute
        args: Command arguments
        cwd: Optional working directory

    Returns:
        Terminal output text

    Raises:
        ModelRetry: If terminal execution fails
    """
    term = await ctx.deps.client_conn.create_terminal(
        command=command, args=args, cwd=cwd, session_id=ctx.deps.session_id
    )
    try:
        await ctx.deps.client_conn.wait_for_terminal_exit(
            session_id=ctx.deps.session_id, terminal_id=term.terminal_id
        )
        output = await ctx.deps.client_conn.terminal_output(
            session_id=ctx.deps.session_id, terminal_id=term.terminal_id
        )
        return output.output
    finally:
        # Always release terminal to prevent resource leak
        await ctx.deps.client_conn.release_terminal(
            session_id=ctx.deps.session_id, terminal_id=term.terminal_id
        )


def _format_typed_result(result: Any) -> str:
    """Serialize a Pydantic result model to JSON.

    JSON is more model-friendly than Python dict reprs for nested structures.

    Args:
        result: Pydantic model instance (TypeCheckResult, RuffResult, etc.)

    Returns:
        JSON-formatted string with indentation
    """
    return result.model_dump_json(indent=2)


async def typecheck_direct(ctx: RunContext[ACPDeps], path: str) -> str:
    """Run ty type checker on a file or directory.

    Returns structured results with error count, errors list, and summary.

    Args:
        ctx: Run context with ACPDeps
        path: File or directory path to type check

    Returns:
        Formatted TypeCheckResult with errors and warnings
    """
    from punie.agent.typed_tools import parse_ty_output

    logger.info(f"🔧 TOOL: typecheck_direct(path={path})")
    try:
        output = await _run_terminal(
            ctx, "ty", ["check", path, "--output-format", "json"]
        )
        result = parse_ty_output(output)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to run typecheck on {path}: {exc}") from exc


async def ruff_check_direct(ctx: RunContext[ACPDeps], path: str) -> str:
    """Run ruff linter on a file or directory.

    Returns structured results with violation count, violations list, and fixable count.

    Args:
        ctx: Run context with ACPDeps
        path: File or directory path to lint

    Returns:
        Formatted RuffResult with violations and fixable info
    """
    from punie.agent.typed_tools import parse_ruff_output

    logger.info(f"🔧 TOOL: ruff_check_direct(path={path})")
    try:
        output = await _run_terminal(ctx, "ruff", ["check", path])
        result = parse_ruff_output(output)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to run ruff check on {path}: {exc}") from exc


async def pytest_run_direct(ctx: RunContext[ACPDeps], path: str) -> str:
    """Run pytest on a file or directory.

    Returns structured results with passed/failed/error counts and test details.

    Args:
        ctx: Run context with ACPDeps
        path: File or directory path to test

    Returns:
        Formatted TestResult with test outcomes and statistics
    """
    from punie.agent.typed_tools import parse_pytest_output

    logger.info(f"🔧 TOOL: pytest_run_direct(path={path})")
    try:
        output = await _run_terminal(ctx, "pytest", [path, "-v", "--tb=short"])
        result = parse_pytest_output(output)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to run pytest on {path}: {exc}") from exc


async def git_status_direct(ctx: RunContext[ACPDeps], path: str = ".") -> str:
    """Get git working tree status.

    Returns structured results with file changes and staged/unstaged info.

    Args:
        ctx: Run context with ACPDeps
        path: Repository path (default: current directory)

    Returns:
        Formatted GitStatusResult with file statuses
    """
    from punie.agent.typed_tools import parse_git_status_output

    logger.info(f"🔧 TOOL: git_status_direct(path={path})")
    try:
        output = await _run_terminal(
            ctx, "git", ["status", "--porcelain"], cwd=path if path != "." else None
        )
        result = parse_git_status_output(output)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to get git status for {path}: {exc}") from exc


async def git_diff_direct(
    ctx: RunContext[ACPDeps], path: str = ".", staged: bool = False
) -> str:
    """Get git diff output.

    Returns structured results with additions/deletions per file.

    Args:
        ctx: Run context with ACPDeps
        path: Repository path (default: current directory)
        staged: Whether to show staged changes (default: unstaged)

    Returns:
        Formatted GitDiffResult with file changes
    """
    from punie.agent.typed_tools import parse_git_diff_output

    logger.info(f"🔧 TOOL: git_diff_direct(path={path}, staged={staged})")
    try:
        args = ["diff"]
        if staged:
            args.append("--staged")

        output = await _run_terminal(ctx, "git", args, cwd=path if path != "." else None)
        result = parse_git_diff_output(output)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to get git diff for {path}: {exc}") from exc


async def git_log_direct(
    ctx: RunContext[ACPDeps], path: str = ".", count: int = 10
) -> str:
    """Get git commit history.

    Returns structured results with commits, hashes, authors, and messages.

    Args:
        ctx: Run context with ACPDeps
        path: Repository path (default: current directory)
        count: Number of commits to show (default: 10)

    Returns:
        Formatted GitLogResult with commit details
    """
    from punie.agent.typed_tools import parse_git_log_output

    logger.info(f"🔧 TOOL: git_log_direct(path={path}, count={count})")
    try:
        output = await _run_terminal(
            ctx,
            "git",
            ["log", "--format=%h|%an|%ad|%s", f"-n{count}"],
            cwd=path if path != "." else None,
        )
        result = parse_git_log_output(output)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to get git log for {path}: {exc}") from exc


async def goto_definition_direct(
    ctx: RunContext[ACPDeps], file_path: str, line: int, column: int, symbol: str
) -> str:
    """Find where a symbol is defined using LSP.

    Returns structured results with definition locations.

    Args:
        ctx: Run context with ACPDeps
        file_path: File containing the symbol
        line: Line number (1-based)
        column: Column number (1-based)
        symbol: Symbol name (for error messages)

    Returns:
        Formatted GotoDefinitionResult with locations
    """
    from punie.agent.lsp_client import get_lsp_client
    from punie.agent.typed_tools import parse_definition_response

    logger.info(f"🔧 TOOL: goto_definition_direct(file_path={file_path}, line={line}, column={column}, symbol={symbol})")
    try:
        client = await get_lsp_client()
        response = await client.goto_definition(file_path, line, column)
        result = parse_definition_response(response, symbol)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to find definition of {symbol} at {file_path}:{line}:{column}: {exc}") from exc


async def find_references_direct(
    ctx: RunContext[ACPDeps], file_path: str, line: int, column: int, symbol: str
) -> str:
    """Find all usages of a symbol using LSP.

    Returns structured results with reference locations.

    Args:
        ctx: Run context with ACPDeps
        file_path: File containing the symbol
        line: Line number (1-based)
        column: Column number (1-based)
        symbol: Symbol name (for error messages)

    Returns:
        Formatted FindReferencesResult with reference list
    """
    from punie.agent.lsp_client import get_lsp_client
    from punie.agent.typed_tools import parse_references_response

    logger.info(f"🔧 TOOL: find_references_direct(file_path={file_path}, line={line}, column={column}, symbol={symbol})")
    try:
        client = await get_lsp_client()
        response = await client.find_references(file_path, line, column)
        result = parse_references_response(response, symbol)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to find references for {symbol} at {file_path}:{line}:{column}: {exc}") from exc


async def hover_direct(
    ctx: RunContext[ACPDeps], file_path: str, line: int, column: int, symbol: str
) -> str:
    """Get type info and docstrings for a symbol using LSP.

    Returns structured results with hover content.

    Args:
        ctx: Run context with ACPDeps
        file_path: File containing the symbol
        line: Line number (1-based)
        column: Column number (1-based)
        symbol: Symbol name (for error messages)

    Returns:
        Formatted HoverResult with type info and docs
    """
    from punie.agent.lsp_client import get_lsp_client
    from punie.agent.typed_tools import parse_hover_response

    logger.info(f"🔧 TOOL: hover_direct(file_path={file_path}, line={line}, column={column}, symbol={symbol})")
    try:
        client = await get_lsp_client()
        response = await client.hover(file_path, line, column)
        result = parse_hover_response(response, symbol)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to get hover info for {symbol} at {file_path}:{line}:{column}: {exc}") from exc


async def document_symbols_direct(ctx: RunContext[ACPDeps], file_path: str) -> str:
    """Get all symbols in a file using LSP.

    Returns structured results with hierarchical symbol tree.

    Args:
        ctx: Run context with ACPDeps
        file_path: File path to analyze

    Returns:
        Formatted DocumentSymbolsResult with symbol hierarchy
    """
    from punie.agent.lsp_client import get_lsp_client
    from punie.agent.typed_tools import parse_document_symbols_response

    logger.info(f"🔧 TOOL: document_symbols_direct(file_path={file_path})")
    try:
        client = await get_lsp_client()
        response = await client.document_symbols(file_path)
        result = parse_document_symbols_response(response, file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to get document symbols for {file_path}: {exc}") from exc


async def workspace_symbols_direct(ctx: RunContext[ACPDeps], query: str) -> str:
    """Search for symbols across the workspace using LSP.

    Returns structured results with matching symbols.

    Args:
        ctx: Run context with ACPDeps
        query: Search query string

    Returns:
        Formatted WorkspaceSymbolsResult with matching symbols
    """
    from punie.agent.lsp_client import get_lsp_client
    from punie.agent.typed_tools import parse_workspace_symbols_response

    logger.info(f"🔧 TOOL: workspace_symbols_direct(query={query})")
    try:
        client = await get_lsp_client()
        response = await client.workspace_symbols(query)
        result = parse_workspace_symbols_response(response, query)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to search workspace symbols for '{query}': {exc}") from exc


async def cst_find_pattern_direct(
    ctx: RunContext[ACPDeps], file_path: str, pattern: str
) -> str:
    """Find nodes matching a pattern in a Python file using LibCST.

    Returns structured results with line numbers and code snippets.

    Supported patterns: "FunctionDef", "ClassDef", "Call", "Decorator",
    "ImportFrom", "call:name", "decorator:name", "import:name"

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to the Python file to analyze
        pattern: Pattern to search for (e.g., "FunctionDef", "call:print")

    Returns:
        Formatted CstFindResult with matches and line numbers
    """
    from punie.cst.code_tools import cst_find_pattern

    logger.info(f"🔧 TOOL: cst_find_pattern_direct(file_path={file_path}, pattern={pattern})")
    try:
        result = cst_find_pattern(file_path, pattern)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to find pattern '{pattern}' in {file_path}: {exc}") from exc


async def cst_rename_direct(
    ctx: RunContext[ACPDeps], file_path: str, old_name: str, new_name: str
) -> str:
    """Rename all occurrences of a symbol in a Python file using LibCST.

    Preserves all whitespace and formatting. Returns the modified source.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to the Python file to modify
        old_name: Symbol name to rename
        new_name: New symbol name

    Returns:
        Formatted CstRenameResult with rename_count and modified_source
    """
    from punie.cst.code_tools import cst_rename

    logger.info(f"🔧 TOOL: cst_rename_direct(file_path={file_path}, old_name={old_name}, new_name={new_name})")
    try:
        result = cst_rename(file_path, old_name, new_name)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to rename '{old_name}' to '{new_name}' in {file_path}: {exc}") from exc


async def cst_add_import_direct(
    ctx: RunContext[ACPDeps], file_path: str, import_stmt: str
) -> str:
    """Add an import statement to a Python file using LibCST (idempotent).

    Only adds the import if not already present. Preserves formatting.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to the Python file to modify
        import_stmt: Import statement to add (e.g., "from typing import Optional")

    Returns:
        Formatted CstAddImportResult with import_added flag and modified_source
    """
    from punie.cst.code_tools import cst_add_import

    logger.info(f"🔧 TOOL: cst_add_import_direct(file_path={file_path}, import_stmt={import_stmt!r})")
    try:
        result = cst_add_import(file_path, import_stmt)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to add import '{import_stmt}' to {file_path}: {exc}") from exc


async def validate_component_direct(ctx: RunContext[ACPDeps], file_path: str) -> str:
    """Validate tdom component patterns in a Python file.

    Checks: @dataclass present, __call__ returns Node, no f-strings in html().

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file containing component definitions

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.tdom import validate_component

    logger.info(f"🔧 TOOL: validate_component_direct(file_path={file_path})")
    try:
        result = validate_component(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to validate component in {file_path}: {exc}") from exc


async def check_render_tree_direct(ctx: RunContext[ACPDeps], file_path: str) -> str:
    """Check component render tree composition in a Python file.

    Verifies component references and composition patterns.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file to analyze

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.tdom import check_render_tree

    logger.info(f"🔧 TOOL: check_render_tree_direct(file_path={file_path})")
    try:
        result = check_render_tree(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to check render tree in {file_path}: {exc}") from exc


async def validate_escape_context_direct(ctx: RunContext[ACPDeps], file_path: str) -> str:
    """Validate that html() calls use safe t-strings, not f-strings.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file to analyze

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.tdom import validate_escape_context

    logger.info(f"🔧 TOOL: validate_escape_context_direct(file_path={file_path})")
    try:
        result = validate_escape_context(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to validate escape context in {file_path}: {exc}") from exc


async def validate_service_registration_direct(
    ctx: RunContext[ACPDeps], file_path: str
) -> str:
    """Validate svcs service registration patterns in a Python file.

    Checks: @injectable present, @dataclass present, Inject[] fields typed correctly.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file containing service definitions

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.svcs import validate_service_registration

    logger.info(f"🔧 TOOL: validate_service_registration_direct(file_path={file_path})")
    try:
        result = validate_service_registration(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to validate service registration in {file_path}: {exc}") from exc


async def check_dependency_graph_direct(ctx: RunContext[ACPDeps], file_path: str) -> str:
    """Check svcs dependency graph for layer violations.

    Verifies services don't depend on components (layer violation).

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file to analyze

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.svcs import check_dependency_graph

    logger.info(f"🔧 TOOL: check_dependency_graph_direct(file_path={file_path})")
    try:
        result = check_dependency_graph(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to check dependency graph in {file_path}: {exc}") from exc


async def validate_injection_site_direct(ctx: RunContext[ACPDeps], file_path: str) -> str:
    """Validate Inject[] field sites reference imported types.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file to analyze

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.svcs import validate_injection_site

    logger.info(f"🔧 TOOL: validate_injection_site_direct(file_path={file_path})")
    try:
        result = validate_injection_site(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to validate injection site in {file_path}: {exc}") from exc


async def validate_middleware_chain_direct(
    ctx: RunContext[ACPDeps], file_path: str
) -> str:
    """Validate tdom-svcs middleware patterns in a Python file.

    Checks: @middleware has categories, correct __call__ signature.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file containing middleware definitions

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.tdom_svcs import validate_middleware_chain

    logger.info(f"🔧 TOOL: validate_middleware_chain_direct(file_path={file_path})")
    try:
        result = validate_middleware_chain(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to validate middleware chain in {file_path}: {exc}") from exc


async def check_di_template_binding_direct(
    ctx: RunContext[ACPDeps], file_path: str
) -> str:
    """Check that DI components have context passed in html() calls.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file to analyze

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.tdom_svcs import check_di_template_binding

    logger.info(f"🔧 TOOL: check_di_template_binding_direct(file_path={file_path})")
    try:
        result = check_di_template_binding(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to check DI template binding in {file_path}: {exc}") from exc


async def validate_route_pattern_direct(ctx: RunContext[ACPDeps], file_path: str) -> str:
    """Validate route patterns in a Python file.

    Checks paths start with / and have balanced braces.

    Args:
        ctx: Run context with ACPDeps
        file_path: Path to Python file containing route definitions

    Returns:
        Formatted DomainValidationResult with issues list
    """
    from punie.cst.validators.tdom_svcs import validate_route_pattern

    logger.info(f"🔧 TOOL: validate_route_pattern_direct(file_path={file_path})")
    try:
        result = validate_route_pattern(file_path)
        return _format_typed_result(result)
    except Exception as exc:
        raise ModelRetry(f"Failed to validate route patterns in {file_path}: {exc}") from exc


def create_direct_toolset() -> FunctionToolset[ACPDeps]:
    """Create toolset for zero-shot models with direct tool calling.

    Used for models like Devstral that use standard function calling rather
    than Code Mode. All typed tools are promoted to direct PydanticAI tools,
    eliminating the execute_code indirection.

    Returns:
        FunctionToolset with 26 tools:
        - 3 base tools: read_file, write_file, run_command
        - 11 Code Tools: typecheck_direct, ruff_check_direct, pytest_run_direct,
          git_status_direct, git_diff_direct, git_log_direct, goto_definition_direct,
          find_references_direct, hover_direct, document_symbols_direct,
          workspace_symbols_direct
        - 3 LibCST code tools: cst_find_pattern_direct, cst_rename_direct,
          cst_add_import_direct
        - 9 domain validators: validate_component_direct, check_render_tree_direct,
          validate_escape_context_direct, validate_service_registration_direct,
          check_dependency_graph_direct, validate_injection_site_direct,
          validate_middleware_chain_direct, check_di_template_binding_direct,
          validate_route_pattern_direct

    Note:
        execute_code and terminal management tools are excluded since zero-shot
        models call tools directly without needing a sandbox.
    """
    return FunctionToolset[ACPDeps](
        tools=[
            # Base file/command tools
            read_file,
            write_file,
            run_command,
            # Direct Code Tools (typed tools promoted to PydanticAI tools)
            typecheck_direct,
            ruff_check_direct,
            pytest_run_direct,
            git_status_direct,
            git_diff_direct,
            git_log_direct,
            goto_definition_direct,
            find_references_direct,
            hover_direct,
            document_symbols_direct,
            workspace_symbols_direct,
            # LibCST code tools (Phase 32)
            cst_find_pattern_direct,
            cst_rename_direct,
            cst_add_import_direct,
            # Domain validators (Phase 32)
            validate_component_direct,
            check_render_tree_direct,
            validate_escape_context_direct,
            validate_service_registration_direct,
            check_dependency_graph_direct,
            validate_injection_site_direct,
            validate_middleware_chain_direct,
            check_di_template_binding_direct,
            validate_route_pattern_direct,
        ]
    )


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
        "execute_code": execute_code,
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
