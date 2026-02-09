"""Timed toolset wrapper for performance measurement."""

from dataclasses import dataclass
from typing import Any

from pydantic_ai.result import RunContext
from pydantic_ai.toolsets import ToolsetTool
from pydantic_ai.toolsets.wrapper import WrapperToolset

from punie.agent.deps import ACPDeps
from punie.perf.collector import PerformanceCollector


@dataclass
class TimedToolset(WrapperToolset[ACPDeps]):
    """Wrapper toolset that records timing for all tool calls."""

    collector: PerformanceCollector

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[ACPDeps],
        tool: ToolsetTool[ACPDeps],
    ) -> Any:
        """Call tool and record timing."""
        self.collector.start_tool(name)
        try:
            result = await self.wrapped.call_tool(name, tool_args, ctx, tool)
            self.collector.end_tool(name, success=True)
            return result
        except Exception as exc:
            self.collector.end_tool(name, success=False, error=str(exc))
            raise
