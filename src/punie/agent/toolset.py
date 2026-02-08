"""Pydantic AI toolset that bridges to ACP Client Protocol.

ACPToolset exposes ACP Client methods as Pydantic AI tools. Phase 3.2 implements
only read_file (wrapping Client.read_text_file). Future phases will add write_file
and terminal tools.
"""

from pydantic_ai import FunctionToolset, RunContext

from punie.acp.helpers import text_block, tool_content
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

    # Clean up tracker
    ctx.deps.tracker.forget(tool_call_id)

    return response.content


def create_toolset() -> FunctionToolset[ACPDeps]:
    """Create ACP toolset with read_file tool.

    Returns a FunctionToolset configured with tools that bridge Pydantic AI
    to ACP Client Protocol. Phase 3.2 includes only read_file.
    """
    return FunctionToolset[ACPDeps](tools=[read_file])


# Alias for backward compatibility
ACPToolset = create_toolset
