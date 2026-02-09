"""Tests for CLI --perf flag and PUNIE_PERF env var."""

import re

import pytest
from typer.testing import CliRunner

from punie.cli import app, resolve_perf


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


def test_ask_with_perf_flag_generates_html(runner, tmp_path, monkeypatch):
    """Test that --perf flag produces an HTML file."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Run ask command with --perf flag using test model
    result = runner.invoke(
        app,
        ["ask", "What is 2+2?", "--model", "test", "--perf"],
    )

    # Check command succeeded
    assert result.exit_code == 0

    # Check that output mentions performance report
    assert "Performance report:" in result.output

    # Find the HTML file
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 1

    # Verify HTML content
    html_content = html_files[0].read_text()
    assert "<!DOCTYPE html>" in html_content
    assert "Punie Performance Report" in html_content
    assert "test" in html_content  # Model name


def test_ask_without_perf_flag_no_html(runner, tmp_path, monkeypatch):
    """Test that without --perf flag, no HTML file is generated."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Run ask command without --perf flag
    result = runner.invoke(
        app,
        ["ask", "What is 2+2?", "--model", "test"],
    )

    # Check command succeeded
    assert result.exit_code == 0

    # Check that no performance report is mentioned
    assert "Performance report:" not in result.output

    # Check that no HTML files were created
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 0


def test_ask_perf_filename_has_timestamp(runner, tmp_path, monkeypatch):
    """Test that performance report filename includes timestamp."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Run ask command with --perf flag
    result = runner.invoke(
        app,
        ["ask", "What is 2+2?", "--model", "test", "--perf"],
    )

    assert result.exit_code == 0

    # Find the HTML file
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 1

    # Verify filename format: punie-perf-YYYYMMDD-HHMMSS.html
    filename = html_files[0].name
    pattern = r"punie-perf-\d{8}-\d{6}\.html"
    assert re.match(pattern, filename), (
        f"Filename {filename} doesn't match expected pattern"
    )


def test_ask_perf_report_path_printed(runner, tmp_path, monkeypatch):
    """Test that the report path is printed to output."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Run ask command with --perf flag
    result = runner.invoke(
        app,
        ["ask", "What is 2+2?", "--model", "test", "--perf"],
    )

    assert result.exit_code == 0

    # Extract the report path from output
    assert "Performance report:" in result.output
    assert "punie-perf-" in result.output
    assert ".html" in result.output


def test_resolve_perf_flag_takes_priority(monkeypatch):
    """Test that CLI flag takes priority over env var."""
    # Set env var to disabled
    monkeypatch.setenv("PUNIE_PERF", "0")

    # Flag should take priority
    assert resolve_perf(True) is True


def test_resolve_perf_env_var_fallback(monkeypatch):
    """Test that env var is used when flag is False."""
    # Set env var to enabled
    monkeypatch.setenv("PUNIE_PERF", "1")

    # Should use env var
    assert resolve_perf(False) is True


def test_resolve_perf_default(monkeypatch):
    """Test that default is False when neither flag nor env var set."""
    # Ensure env var is not set
    monkeypatch.delenv("PUNIE_PERF", raising=False)

    # Should default to False
    assert resolve_perf(False) is False


def test_resolve_perf_env_var_zero(monkeypatch):
    """Test that PUNIE_PERF=0 disables perf."""
    monkeypatch.setenv("PUNIE_PERF", "0")

    assert resolve_perf(False) is False


def test_resolve_perf_env_var_other_values(monkeypatch):
    """Test that only PUNIE_PERF=1 enables perf."""
    # Test various non-1 values
    for value in ["true", "True", "yes", "on", "2", ""]:
        monkeypatch.setenv("PUNIE_PERF", value)
        assert resolve_perf(False) is False, f"Expected False for PUNIE_PERF={value}"


def test_ask_with_env_var_generates_html(runner, tmp_path, monkeypatch):
    """Test that PUNIE_PERF=1 env var produces HTML file."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Set env var
    monkeypatch.setenv("PUNIE_PERF", "1")

    # Run ask command without --perf flag
    result = runner.invoke(
        app,
        ["ask", "What is 2+2?", "--model", "test"],
        env={"PUNIE_PERF": "1"},
    )

    # Check command succeeded
    assert result.exit_code == 0

    # Check that output mentions performance report
    assert "Performance report:" in result.output

    # Find the HTML file
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 1


def test_ask_flag_overrides_env_var(runner, tmp_path, monkeypatch):
    """Test that --perf flag works even when env var is 0."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Set env var to disabled
    monkeypatch.setenv("PUNIE_PERF", "0")

    # Run with --perf flag (should override env var)
    result = runner.invoke(
        app,
        ["ask", "What is 2+2?", "--model", "test", "--perf"],
        env={"PUNIE_PERF": "0"},
    )

    assert result.exit_code == 0

    # Should still generate report
    assert "Performance report:" in result.output
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 1
