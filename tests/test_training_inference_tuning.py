"""Tests for inference parameter tuning."""

from punie.training.inference_tuning import InferenceGrid, InferenceResult
from punie.training.eval_results import EvalReport, EvalResult
from punie.training.server_config import ServerConfig
from datetime import datetime


def test_inference_grid_frozen():
    """InferenceGrid is immutable."""
    grid = InferenceGrid()

    try:
        grid.temperatures = (0.5,)  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_inference_grid_defaults():
    """InferenceGrid has sensible defaults."""
    grid = InferenceGrid()

    assert grid.temperatures == (0.0, 0.1, 0.3, 0.7)
    assert grid.top_ps == (0.9, 0.95, 1.0)
    assert grid.repetition_penalties == (1.0, 1.1, 1.2)
    assert grid.max_kv_sizes == (None,)


def test_inference_grid_total_combinations():
    """InferenceGrid calculates total combinations correctly."""
    grid = InferenceGrid(
        temperatures=(0.0, 0.5),
        top_ps=(0.9, 1.0),
        repetition_penalties=(1.0,),
        max_kv_sizes=(None, 2048),
    )

    # 2 * 2 * 1 * 2 = 8
    assert grid.total_combinations == 8


def test_inference_grid_custom():
    """InferenceGrid with custom values."""
    grid = InferenceGrid(
        temperatures=(0.0,),
        top_ps=(1.0,),
        repetition_penalties=(1.0, 1.1),
        max_kv_sizes=(None,),
    )

    assert len(grid.temperatures) == 1
    assert len(grid.top_ps) == 1
    assert len(grid.repetition_penalties) == 2
    assert len(grid.max_kv_sizes) == 1
    assert grid.total_combinations == 2  # 1 * 1 * 2 * 1


def test_inference_result_frozen():
    """InferenceResult is immutable."""
    config = ServerConfig(model_path="test")
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="test",
        timestamp=datetime.now(),
        results=(),
    )

    result = InferenceResult(
        server_config=config,
        eval_report=report,
        temperature=0.0,
        top_p=0.9,
        repetition_penalty=1.0,
    )

    try:
        result.temperature = 0.5  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_inference_result_basic():
    """InferenceResult stores all parameters."""
    config = ServerConfig(
        model_path="test-model",
        port=8080,
        max_kv_size=2048,
        repetition_penalty=1.1,
    )

    report = EvalReport(
        model_name="test-model",
        adapter_path=None,
        suite_name="test",
        timestamp=datetime.now(),
        results=(
            EvalResult("p1", "response", (), 100.0, 0.8, True),
        ),
    )

    result = InferenceResult(
        server_config=config,
        eval_report=report,
        temperature=0.3,
        top_p=0.95,
        repetition_penalty=1.1,
    )

    assert result.server_config.model_path == "test-model"
    assert result.server_config.max_kv_size == 2048
    assert result.server_config.repetition_penalty == 1.1
    assert result.eval_report.overall_score == 0.8
    assert result.temperature == 0.3
    assert result.top_p == 0.95
    assert result.repetition_penalty == 1.1
