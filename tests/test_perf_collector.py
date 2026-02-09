"""Tests for performance collector."""

import time

import pytest

from punie.perf.collector import PerformanceCollector


def test_collector_lifecycle():
    """Test basic collector lifecycle: start tool, end tool, report."""
    collector = PerformanceCollector()
    collector.start_prompt("test-model", "local")

    collector.start_tool("read_file")
    time.sleep(0.01)  # Simulate work
    collector.end_tool("read_file", success=True)

    collector.end_prompt()
    report = collector.report()

    assert report.model_name == "test-model"
    assert report.backend == "local"
    assert len(report.tool_timings) == 1
    assert report.tool_timings[0].tool_name == "read_file"
    assert report.tool_timings[0].success is True
    assert report.tool_timings[0].duration_ms >= 10


def test_collector_multiple_tools():
    """Test collector with multiple tool calls."""
    collector = PerformanceCollector()
    collector.start_prompt("test-model", "ide")

    tools = ["read_file", "list_directory", "search_files"]
    for tool in tools:
        collector.start_tool(tool)
        time.sleep(0.005)
        collector.end_tool(tool, success=True)

    collector.end_prompt()
    report = collector.report()

    assert len(report.tool_timings) == 3
    assert [t.tool_name for t in report.tool_timings] == tools
    assert all(t.success for t in report.tool_timings)


def test_collector_tool_error():
    """Test collector records tool errors."""
    collector = PerformanceCollector()
    collector.start_prompt("test-model", "local")

    collector.start_tool("read_file")
    collector.end_tool("read_file", success=False, error="File not found")

    collector.end_prompt()
    report = collector.report()

    assert len(report.tool_timings) == 1
    timing = report.tool_timings[0]
    assert timing.success is False
    assert timing.error == "File not found"


def test_collector_timing_accuracy():
    """Test that timing measurements are reasonably accurate."""
    collector = PerformanceCollector()
    collector.start_prompt("test-model", "local")

    sleep_time = 0.02  # 20ms
    collector.start_tool("slow_tool")
    time.sleep(sleep_time)
    collector.end_tool("slow_tool")

    collector.end_prompt()
    report = collector.report()

    # Duration should be at least sleep_time (with some tolerance for execution overhead)
    assert report.tool_timings[0].duration_ms >= sleep_time * 1000 * 0.9


def test_collector_frozen_snapshots():
    """Test that report returns frozen immutable snapshots."""
    collector = PerformanceCollector()
    collector.start_prompt("test-model", "local")

    collector.start_tool("tool1")
    collector.end_tool("tool1")

    collector.end_prompt()
    report = collector.report()

    # Verify frozen
    with pytest.raises(AttributeError):
        report.model_name = "changed"  # type: ignore

    with pytest.raises(AttributeError):
        report.tool_timings[0].tool_name = "changed"  # type: ignore


def test_collector_report_without_start_raises():
    """Test that generating report without starting prompt raises error."""
    collector = PerformanceCollector()

    with pytest.raises(ValueError, match="prompt timing not started"):
        collector.report()


def test_collector_report_without_end_raises():
    """Test that generating report without ending prompt raises error."""
    collector = PerformanceCollector()
    collector.start_prompt("test-model", "local")

    with pytest.raises(ValueError, match="not ended"):
        collector.report()


def test_collector_prompt_duration():
    """Test that prompt duration includes all tool time."""
    collector = PerformanceCollector()
    collector.start_prompt("test-model", "local")

    collector.start_tool("tool1")
    time.sleep(0.01)
    collector.end_tool("tool1")

    time.sleep(0.01)  # Simulate model thinking

    collector.start_tool("tool2")
    time.sleep(0.01)
    collector.end_tool("tool2")

    collector.end_prompt()
    report = collector.report()

    # Total duration should be >= sum of tool durations + think time
    total_tool_time = sum(t.duration_ms for t in report.tool_timings)
    assert report.duration_ms >= total_tool_time
    assert report.duration_ms >= 30  # At least 30ms total
