"""Tests for dataset validation functions."""

from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_validation import validate_dataset, validate_example


def test_validate_example_valid():
    """Valid example passes validation."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
        )
    )

    errors = validate_example(example)
    assert errors == []


def test_validate_example_too_few_messages():
    """Example with <2 messages fails validation."""
    example = TrainingExample(
        messages=(ChatMessage(role="user", content="Hello"),)
    )

    errors = validate_example(example)
    assert len(errors) > 0
    assert "at least 2" in errors[0]


def test_validate_example_last_not_assistant():
    """Example where last message isn't from assistant fails."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="user", content="Are you there?"),
        )
    )

    errors = validate_example(example)
    assert any("should be 'assistant'" in e for e in errors)


def test_validate_example_invalid_role():
    """Example with invalid role fails validation."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="bot", content="Hello"),  # Invalid role
            ChatMessage(role="assistant", content="Hi"),
        )
    )

    errors = validate_example(example)
    assert any("invalid role" in e for e in errors)


def test_validate_example_empty_content():
    """Example with empty content fails validation."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="  "),  # Empty/whitespace only
            ChatMessage(role="assistant", content="Hi"),
        )
    )

    errors = validate_example(example)
    assert any("empty content" in e for e in errors)


def test_validate_example_with_system():
    """Example with system message is valid."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi!"),
        )
    )

    errors = validate_example(example)
    assert errors == []


def test_validate_dataset_valid():
    """Valid dataset passes validation."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi!"),
        )
    )

    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(example,),
        valid=(),
        test=(),
    )

    errors = validate_dataset(dataset)
    assert errors == []


def test_validate_dataset_all_empty():
    """Dataset with all empty splits fails."""
    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(),
        valid=(),
        test=(),
    )

    errors = validate_dataset(dataset)
    assert any("no examples" in e for e in errors)


def test_validate_dataset_no_training():
    """Dataset with no training examples fails."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi!"),
        )
    )

    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(),
        valid=(example,),
        test=(),
    )

    errors = validate_dataset(dataset)
    assert any("Training split is empty" in e for e in errors)


def test_validate_dataset_invalid_examples():
    """Dataset with invalid examples reports errors."""
    bad_example = TrainingExample(
        messages=(ChatMessage(role="user", content="Only one message"),)
    )

    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(bad_example,),
        valid=(),
        test=(),
    )

    errors = validate_dataset(dataset)
    assert any("train[0]" in e for e in errors)
    assert any("at least 2" in e for e in errors)
