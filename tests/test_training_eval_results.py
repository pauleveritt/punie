"""Tests for evaluation results dataclasses."""

from datetime import datetime

from punie.training.eval_results import EvalReport, EvalResult


def test_eval_result_frozen():
    """EvalResult instances are immutable."""
    result = EvalResult(
        prompt_id="test-01",
        response_text="Hello",
        tool_calls_made=(),
        duration_ms=100.0,
        score=0.8,
        success=True,
    )

    try:
        result.score = 0.9  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_eval_result_basic():
    """EvalResult stores all fields."""
    result = EvalResult(
        prompt_id="test-01",
        response_text="Response text",
        tool_calls_made=("read_file", "write_file"),
        duration_ms=250.5,
        score=0.75,
        success=True,
    )

    assert result.prompt_id == "test-01"
    assert result.response_text == "Response text"
    assert result.tool_calls_made == ("read_file", "write_file")
    assert result.duration_ms == 250.5
    assert result.score == 0.75
    assert result.success is True


def test_eval_result_failure():
    """EvalResult can represent failure."""
    result = EvalResult(
        prompt_id="test-01",
        response_text="",
        tool_calls_made=(),
        duration_ms=0.0,
        score=0.0,
        success=False,
    )

    assert result.success is False


def test_eval_report_frozen():
    """EvalReport instances are immutable."""
    result = EvalResult(
        prompt_id="test-01",
        response_text="Hello",
        tool_calls_made=(),
        duration_ms=100.0,
        score=0.8,
        success=True,
    )
    report = EvalReport(
        model_name="test-model",
        adapter_path=None,
        suite_name="baseline",
        timestamp=datetime.now(),
        results=(result,),
    )

    try:
        report.model_name = "other-model"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_eval_report_overall_score():
    """EvalReport.overall_score calculates average."""
    results = (
        EvalResult("test-01", "A", (), 100.0, 0.8, True),
        EvalResult("test-02", "B", (), 100.0, 0.6, True),
        EvalResult("test-03", "C", (), 100.0, 1.0, True),
    )
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="baseline",
        timestamp=datetime.now(),
        results=results,
    )

    assert report.overall_score == (0.8 + 0.6 + 1.0) / 3


def test_eval_report_overall_score_empty():
    """EvalReport.overall_score returns 0.0 for empty results."""
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="baseline",
        timestamp=datetime.now(),
        results=(),
    )

    assert report.overall_score == 0.0


def test_eval_report_success_rate():
    """EvalReport.success_rate calculates fraction of successes."""
    results = (
        EvalResult("test-01", "A", (), 100.0, 0.8, True),
        EvalResult("test-02", "B", (), 100.0, 0.6, True),
        EvalResult("test-03", "C", (), 100.0, 0.0, False),
        EvalResult("test-04", "D", (), 100.0, 0.9, True),
    )
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="baseline",
        timestamp=datetime.now(),
        results=results,
    )

    assert report.success_rate == 0.75  # 3 out of 4


def test_eval_report_success_rate_empty():
    """EvalReport.success_rate returns 0.0 for empty results."""
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="baseline",
        timestamp=datetime.now(),
        results=(),
    )

    assert report.success_rate == 0.0


def test_eval_report_score_by_category():
    """EvalReport.score_by_category calculates per-category averages."""
    results = (
        EvalResult("tool-01", "A", (), 100.0, 0.8, True),
        EvalResult("tool-02", "B", (), 100.0, 0.6, True),
        EvalResult("code-01", "C", (), 100.0, 1.0, True),
    )
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="baseline",
        timestamp=datetime.now(),
        results=results,
    )

    # Group results by category (simulating what the caller would do)
    category_results = {
        "tool_calling": [results[0], results[1]],
        "code_generation": [results[2]],
    }

    scores = report.score_by_category(category_results)
    assert scores["tool_calling"] == (0.8 + 0.6) / 2
    assert scores["code_generation"] == 1.0


def test_eval_report_score_by_category_empty():
    """EvalReport.score_by_category handles empty categories."""
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="baseline",
        timestamp=datetime.now(),
        results=(),
    )

    category_results = {
        "tool_calling": [],
        "code_generation": [],
    }

    scores = report.score_by_category(category_results)
    assert scores["tool_calling"] == 0.0
    assert scores["code_generation"] == 0.0


def test_eval_report_with_adapter():
    """EvalReport can store adapter path."""
    result = EvalResult("test-01", "A", (), 100.0, 0.8, True)
    report = EvalReport(
        model_name="test-model",
        adapter_path="/path/to/adapter",
        suite_name="baseline",
        timestamp=datetime.now(),
        results=(result,),
    )

    assert report.adapter_path == "/path/to/adapter"
