"""Tests for evaluation report comparison."""

from datetime import datetime

from punie.training.eval_comparison import compare_reports
from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_results import EvalReport, EvalResult


def test_compare_reports_empty():
    """compare_reports with no reports."""
    suite = EvalSuite(name="test", prompts=())
    html = compare_reports([], suite)
    assert "<p>No reports to compare</p>" in html


def test_compare_reports_single():
    """compare_reports with one report."""
    suite = EvalSuite(
        name="test",
        prompts=(
            EvalPrompt(
                id="p1",
                category="testing",
                prompt_text="Test prompt",
            ),
        ),
    )

    report = EvalReport(
        model_name="test-model",
        adapter_path=None,
        suite_name="test",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        results=(
            EvalResult(
                prompt_id="p1",
                response_text="response",
                tool_calls_made=(),
                duration_ms=100.0,
                score=0.8,
                success=True,
            ),
        ),
    )

    html = compare_reports([report], suite)

    assert "test-model" in html
    assert "80.0%" in html or "80%" in html  # Overall score
    assert "100.0%" in html or "100%" in html  # Success rate
    assert "2024-01-01" in html


def test_compare_reports_multiple_with_delta():
    """compare_reports shows delta between reports."""
    suite = EvalSuite(
        name="test",
        prompts=(
            EvalPrompt(id="p1", category="cat1", prompt_text="Test 1"),
            EvalPrompt(id="p2", category="cat1", prompt_text="Test 2"),
        ),
    )

    report1 = EvalReport(
        model_name="model",
        adapter_path=None,
        suite_name="test",
        timestamp=datetime(2024, 1, 1),
        results=(
            EvalResult("p1", "resp", (), 100.0, 0.5, True),
            EvalResult("p2", "resp", (), 100.0, 0.5, True),
        ),
    )

    report2 = EvalReport(
        model_name="model",
        adapter_path="adapters/v1",
        suite_name="test",
        timestamp=datetime(2024, 1, 2),
        results=(
            EvalResult("p1", "resp", (), 100.0, 0.7, True),
            EvalResult("p2", "resp", (), 100.0, 0.9, True),
        ),
    )

    html = compare_reports([report1, report2], suite)

    # Should show both reports
    assert "adapters/v1" in html

    # Second report should show delta
    assert "delta" in html.lower()


def test_compare_reports_category_breakdown():
    """compare_reports shows category breakdown."""
    suite = EvalSuite(
        name="test",
        prompts=(
            EvalPrompt(id="p1", category="cat1", prompt_text="Test 1"),
            EvalPrompt(id="p2", category="cat2", prompt_text="Test 2"),
        ),
    )

    report = EvalReport(
        model_name="model",
        adapter_path=None,
        suite_name="test",
        timestamp=datetime(2024, 1, 1),
        results=(
            EvalResult("p1", "resp", (), 100.0, 1.0, True),
            EvalResult("p2", "resp", (), 100.0, 0.5, True),
        ),
    )

    html = compare_reports([report], suite)

    # Should show categories
    assert "cat1" in html
    assert "cat2" in html

    # Should show scores for each category
    assert "100.0%" in html or "100%" in html  # cat1 score
    assert "50.0%" in html or "50%" in html  # cat2 score
