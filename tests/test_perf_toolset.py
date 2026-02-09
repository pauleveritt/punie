"""Tests for timed toolset wrapper."""

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic_ai.result import RunContext
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool

from punie.agent.deps import ACPDeps
from punie.perf.collector import PerformanceCollector
from punie.perf.toolset import TimedToolset


@dataclass
class FakeToolset(AbstractToolset[ACPDeps]):
    """Fake toolset for testing."""

    mock_result: Any = None
    should_raise: Exception | None = None

    @property
    def id(self) -> str:
        """Return toolset ID."""
        return "fake-toolset"

    def get_tools(self) -> list[ToolsetTool[ACPDeps]]:
        """Return empty tool list."""
        return []

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[ACPDeps],
        tool: ToolsetTool[ACPDeps],
    ) -> Any:
        """Fake tool call."""
        if self.should_raise:
            raise self.should_raise
        return self.mock_result


@pytest.fixture
def collector():
    """Create a performance collector."""
    return PerformanceCollector()


@pytest.fixture
def fake_ctx():
    """Create a fake RunContext."""
    return Mock(spec=RunContext)


@pytest.fixture
def fake_tool():
    """Create a fake ToolsetTool."""
    return Mock(spec=ToolsetTool)


@pytest.mark.asyncio
async def test_timed_toolset_records_successful_call(collector, fake_ctx, fake_tool):
    """Test that TimedToolset records timing for successful calls."""
    fake_toolset = FakeToolset(mock_result="test_result")
    timed = TimedToolset(wrapped=fake_toolset, collector=collector)

    collector.start_prompt("test-model", "local")
    result = await timed.call_tool("read_file", {}, fake_ctx, fake_tool)
    collector.end_prompt()

    assert result == "test_result"
    report = collector.report()
    assert len(report.tool_timings) == 1
    assert report.tool_timings[0].tool_name == "read_file"
    assert report.tool_timings[0].success is True
    assert report.tool_timings[0].duration_ms > 0


@pytest.mark.asyncio
async def test_timed_toolset_records_failed_call(collector, fake_ctx, fake_tool):
    """Test that TimedToolset records timing for failed calls."""
    error = ValueError("test error")
    fake_toolset = FakeToolset(should_raise=error)
    timed = TimedToolset(wrapped=fake_toolset, collector=collector)

    collector.start_prompt("test-model", "local")
    with pytest.raises(ValueError, match="test error"):
        await timed.call_tool("read_file", {}, fake_ctx, fake_tool)
    collector.end_prompt()

    report = collector.report()
    assert len(report.tool_timings) == 1
    timing = report.tool_timings[0]
    assert timing.tool_name == "read_file"
    assert timing.success is False
    assert timing.error == "test error"
    assert timing.duration_ms > 0


@pytest.mark.asyncio
async def test_timed_toolset_records_multiple_calls(collector, fake_ctx, fake_tool):
    """Test that TimedToolset records timing for multiple tool calls."""
    fake_toolset = FakeToolset(mock_result="result")
    timed = TimedToolset(wrapped=fake_toolset, collector=collector)

    collector.start_prompt("test-model", "local")
    await timed.call_tool("read_file", {}, fake_ctx, fake_tool)
    await timed.call_tool("list_directory", {}, fake_ctx, fake_tool)
    await timed.call_tool("search_files", {}, fake_ctx, fake_tool)
    collector.end_prompt()

    report = collector.report()
    assert len(report.tool_timings) == 3
    assert [t.tool_name for t in report.tool_timings] == [
        "read_file",
        "list_directory",
        "search_files",
    ]
    assert all(t.success for t in report.tool_timings)


@pytest.mark.asyncio
async def test_timed_toolset_preserves_return_value(collector, fake_ctx, fake_tool):
    """Test that TimedToolset preserves the wrapped toolset's return value."""
    expected_result = {"data": [1, 2, 3], "status": "ok"}
    fake_toolset = FakeToolset(mock_result=expected_result)
    timed = TimedToolset(wrapped=fake_toolset, collector=collector)

    collector.start_prompt("test-model", "local")
    result = await timed.call_tool("complex_tool", {}, fake_ctx, fake_tool)
    collector.end_prompt()

    assert result == expected_result
