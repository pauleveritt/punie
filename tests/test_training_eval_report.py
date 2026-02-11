"""Tests for evaluation HTML report generation."""

from datetime import datetime

from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_results import EvalReport, EvalResult


def test_generate_eval_html_report():
    """generate_eval_html_report produces valid HTML."""
    # Create a simple suite and report
    prompts = (
        EvalPrompt(
            id="tool-01",
            category="tool_calling",
            prompt_text="Test tool calling",
            expected_tool_calls=("read_file",),
        ),
        EvalPrompt(
            id="code-01",
            category="code_generation",
            prompt_text="Test code generation",
            expected_keywords=("def",),
        ),
    )
    suite = EvalSuite(name="test-suite", prompts=prompts)

    results = (
        EvalResult(
            prompt_id="tool-01",
            response_text="I called the read_file tool",
            tool_calls_made=("read_file",),
            duration_ms=100.0,
            score=0.9,
            success=True,
        ),
        EvalResult(
            prompt_id="code-01",
            response_text="def foo(): pass",
            tool_calls_made=(),
            duration_ms=150.0,
            score=0.8,
            success=True,
        ),
    )
    report = EvalReport(
        model_name="test-model",
        adapter_path=None,
        suite_name="test-suite",
        timestamp=datetime.now(),
        results=results,
    )

    html = generate_eval_html_report(report, suite)

    # Verify it's valid HTML
    assert html.startswith("<!DOCTYPE html>")
    assert "<html" in html
    assert "</html>" in html

    # Verify key content is present
    assert "test-suite" in html
    assert "test-model" in html
    assert "tool-01" in html
    assert "code-01" in html
    assert "90.00%" in html or "0.90" in html  # Score formatting
    assert "Tool Calling" in html
    assert "Code Generation" in html


def test_generate_eval_html_report_with_adapter():
    """generate_eval_html_report includes adapter path."""
    prompt = EvalPrompt(id="test-01", category="test", prompt_text="Test")
    suite = EvalSuite(name="test-suite", prompts=(prompt,))

    result = EvalResult(
        prompt_id="test-01",
        response_text="Response",
        tool_calls_made=(),
        duration_ms=100.0,
        score=0.8,
        success=True,
    )
    report = EvalReport(
        model_name="test-model",
        adapter_path="/path/to/adapter",
        suite_name="test-suite",
        timestamp=datetime.now(),
        results=(result,),
    )

    html = generate_eval_html_report(report, suite)

    assert "/path/to/adapter" in html


def test_generate_eval_html_report_with_failures():
    """generate_eval_html_report handles failed results."""
    prompt = EvalPrompt(id="test-01", category="test", prompt_text="Test")
    suite = EvalSuite(name="test-suite", prompts=(prompt,))

    result = EvalResult(
        prompt_id="test-01",
        response_text="Error: Timeout",
        tool_calls_made=(),
        duration_ms=5000.0,
        score=0.0,
        success=False,
    )
    report = EvalReport(
        model_name="test-model",
        adapter_path=None,
        suite_name="test-suite",
        timestamp=datetime.now(),
        results=(result,),
    )

    html = generate_eval_html_report(report, suite)

    assert "✗" in html or "failure" in html
    assert "Error: Timeout" in html
