"""Tests for hyperparameter tuning."""

from punie.training.hyperparam import HyperparamGrid, TrainingLog, parse_training_log


def test_hyperparam_grid_frozen():
    """HyperparamGrid is immutable."""
    grid = HyperparamGrid()

    try:
        grid.learning_rates = (1e-4,)  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_hyperparam_grid_defaults():
    """HyperparamGrid has sensible defaults."""
    grid = HyperparamGrid()

    assert grid.learning_rates == (1e-5, 5e-5, 1e-4)
    assert grid.lora_ranks == (4, 8, 16)
    assert grid.num_iters == (50, 100, 200)
    assert grid.batch_sizes == (2, 4)


def test_hyperparam_grid_total_combinations():
    """HyperparamGrid calculates total combinations correctly."""
    grid = HyperparamGrid(
        learning_rates=(1e-5, 5e-5),
        lora_ranks=(4, 8),
        num_iters=(50,),
        batch_sizes=(2,),
    )

    # 2 * 2 * 1 * 1 = 4
    assert grid.total_combinations == 4


def test_hyperparam_grid_custom():
    """HyperparamGrid with custom values."""
    grid = HyperparamGrid(
        learning_rates=(1e-4,),
        lora_ranks=(16,),
        num_iters=(100, 200),
        batch_sizes=(4, 8),
    )

    assert len(grid.learning_rates) == 1
    assert len(grid.lora_ranks) == 1
    assert len(grid.num_iters) == 2
    assert len(grid.batch_sizes) == 2
    assert grid.total_combinations == 4  # 1 * 1 * 2 * 2


def test_training_log_frozen():
    """TrainingLog is immutable."""
    log = TrainingLog(iteration=10, train_loss=2.5)

    try:
        log.iteration = 20  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_training_log_with_val_loss():
    """TrainingLog with validation loss."""
    log = TrainingLog(iteration=10, train_loss=2.5, val_loss=2.8)

    assert log.iteration == 10
    assert log.train_loss == 2.5
    assert log.val_loss == 2.8


def test_training_log_without_val_loss():
    """TrainingLog without validation loss."""
    log = TrainingLog(iteration=10, train_loss=2.5)

    assert log.iteration == 10
    assert log.train_loss == 2.5
    assert log.val_loss is None


def test_parse_training_log_empty():
    """parse_training_log with empty output."""
    logs = parse_training_log("")
    assert logs == ()


def test_parse_training_log_single_iter():
    """parse_training_log with single iteration."""
    output = "Iter 10: Train loss 2.345, Val loss 2.567"
    logs = parse_training_log(output)

    assert len(logs) == 1
    assert logs[0].iteration == 10
    assert logs[0].train_loss == 2.345
    assert logs[0].val_loss == 2.567


def test_parse_training_log_multiple_iters():
    """parse_training_log with multiple iterations."""
    output = """
    Iter 10: Train loss 2.345, Val loss 2.567
    Iter 20: Train loss 2.123, Val loss 2.345
    Iter 30: Train loss 1.987, Val loss 2.234
    """
    logs = parse_training_log(output)

    assert len(logs) == 3
    assert logs[0].iteration == 10
    assert logs[0].train_loss == 2.345
    assert logs[1].iteration == 20
    assert logs[1].train_loss == 2.123
    assert logs[2].iteration == 30
    assert logs[2].train_loss == 1.987


def test_parse_training_log_train_only():
    """parse_training_log with only train loss."""
    output = "Iter 10: Train loss 2.345"
    logs = parse_training_log(output)

    assert len(logs) == 1
    assert logs[0].iteration == 10
    assert logs[0].train_loss == 2.345
    assert logs[0].val_loss is None


def test_parse_training_log_mixed_content():
    """parse_training_log with mixed content."""
    output = """
    Loading model...
    Iter 10: Train loss 2.345, Val loss 2.567
    Some random output
    Iter 20: Train loss 2.123
    More output
    Iter 30: Train loss 1.987, Val loss 2.100
    Done!
    """
    logs = parse_training_log(output)

    assert len(logs) == 3
    assert logs[0].iteration == 10
    assert logs[1].iteration == 20
    assert logs[1].val_loss is None
    assert logs[2].iteration == 30


def test_parse_training_log_malformed_lines():
    """parse_training_log skips malformed lines."""
    output = """
    Iter: Train loss 2.345
    Iter 10 Train loss 2.345
    Iter 20: Train loss invalid
    Iter 30: Train loss 1.987, Val loss 2.100
    """
    logs = parse_training_log(output)

    # Only the last line should parse correctly
    assert len(logs) == 1
    assert logs[0].iteration == 30
