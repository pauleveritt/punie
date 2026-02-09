"""Tests for HTML report generation."""

from punie.perf.collector import PromptTiming, ToolTiming
from punie.perf.report import generate_html_report


def test_generate_html_report_basic():
    """Test HTML report generation with basic timing data."""
    timing = PromptTiming(
        started_at=1000.0,
        ended_at=1100.0,
        duration_ms=100.0,
        model_name="test-model",
        backend="local",
        tool_timings=(),
    )

    html = generate_html_report(timing)

    assert "<!DOCTYPE html>" in html
    assert "test-model" in html
    assert "local" in html
    assert "100.00 ms" in html


def test_generate_html_report_with_tools():
    """Test HTML report generation with tool timings."""
    tool1 = ToolTiming(
        tool_name="read_file",
        started_at=1000.0,
        ended_at=1020.0,
        duration_ms=20.0,
        success=True,
    )
    tool2 = ToolTiming(
        tool_name="list_directory",
        started_at=1030.0,
        ended_at=1050.0,
        duration_ms=20.0,
        success=True,
    )

    timing = PromptTiming(
        started_at=1000.0,
        ended_at=1100.0,
        duration_ms=100.0,
        model_name="gpt-4",
        backend="ide",
        tool_timings=(tool1, tool2),
    )

    html = generate_html_report(timing)

    assert "read_file" in html
    assert "list_directory" in html
    assert "20.00" in html
    assert "gpt-4" in html
    assert "ide" in html


def test_generate_html_report_with_failure():
    """Test HTML report generation with failed tool call."""
    tool_fail = ToolTiming(
        tool_name="read_file",
        started_at=1000.0,
        ended_at=1020.0,
        duration_ms=20.0,
        success=False,
        error="File not found",
    )

    timing = PromptTiming(
        started_at=1000.0,
        ended_at=1100.0,
        duration_ms=100.0,
        model_name="test-model",
        backend="local",
        tool_timings=(tool_fail,),
    )

    html = generate_html_report(timing)

    assert "File not found" in html
    assert "✗" in html or "failure" in html


def test_generate_html_report_timing_breakdown():
    """Test that timing breakdown is calculated correctly."""
    tool1 = ToolTiming(
        tool_name="tool1",
        started_at=1000.0,
        ended_at=1030.0,
        duration_ms=30.0,
        success=True,
    )
    tool2 = ToolTiming(
        tool_name="tool2",
        started_at=1040.0,
        ended_at=1060.0,
        duration_ms=20.0,
        success=True,
    )

    timing = PromptTiming(
        started_at=1000.0,
        ended_at=1100.0,
        duration_ms=100.0,  # Total 100ms
        model_name="test-model",
        backend="local",
        tool_timings=(tool1, tool2),  # 50ms total tool time
    )

    html = generate_html_report(timing)

    # Total tool time: 50ms, model think time: 50ms
    assert "50.00 ms" in html  # Should appear twice (tool time and model time)


def test_generate_html_report_embedded_css():
    """Test that report has embedded CSS for standalone viewing."""
    timing = PromptTiming(
        started_at=1000.0,
        ended_at=1100.0,
        duration_ms=100.0,
        model_name="test-model",
        backend="local",
        tool_timings=(),
    )

    html = generate_html_report(timing)

    assert "<style>" in html
    assert "font-family" in html
    assert "background" in html
    assert "</style>" in html


def test_generate_html_report_table_structure():
    """Test that report includes proper table structure."""
    tool1 = ToolTiming(
        tool_name="read_file",
        started_at=1000.0,
        ended_at=1020.0,
        duration_ms=20.0,
        success=True,
    )

    timing = PromptTiming(
        started_at=1000.0,
        ended_at=1100.0,
        duration_ms=100.0,
        model_name="test-model",
        backend="local",
        tool_timings=(tool1,),
    )

    html = generate_html_report(timing)

    assert "<table>" in html
    assert "<thead>" in html
    assert "<tbody>" in html
    assert "Tool Name" in html
    assert "Duration" in html
    assert "Status" in html
