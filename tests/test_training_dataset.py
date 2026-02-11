"""Tests for training dataset dataclasses."""

import pytest

from punie.training.dataset import ChatMessage, DatasetStats, TrainingDataset, TrainingExample


def test_chat_message_frozen():
    """ChatMessage instances are immutable."""
    msg = ChatMessage(role="user", content="Hello")

    try:
        msg.role = "assistant"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_chat_message_basic():
    """ChatMessage stores role and content."""
    msg = ChatMessage(role="system", content="You are a helpful assistant")

    assert msg.role == "system"
    assert msg.content == "You are a helpful assistant"


def test_training_example_frozen():
    """TrainingExample instances are immutable."""
    msg = ChatMessage(role="user", content="Test")
    example = TrainingExample(messages=(msg,))

    try:
        example.messages = ()  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_training_example_to_jsonl_dict():
    """TrainingExample.to_jsonl_dict() produces correct format."""
    messages = (
        ChatMessage(role="system", content="You are helpful"),
        ChatMessage(role="user", content="What is 2+2?"),
        ChatMessage(role="assistant", content="4"),
    )
    example = TrainingExample(messages=messages)

    result = example.to_jsonl_dict()

    assert result == {
        "messages": [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
        ]
    }


def test_training_example_single_message():
    """TrainingExample works with single message."""
    msg = ChatMessage(role="user", content="Hello")
    example = TrainingExample(messages=(msg,))

    result = example.to_jsonl_dict()
    assert len(result["messages"]) == 1
    assert result["messages"][0]["content"] == "Hello"


def test_training_dataset_frozen():
    """TrainingDataset instances are immutable."""
    example = TrainingExample(messages=(ChatMessage(role="user", content="Test"),))
    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(example,),
        valid=(),
        test=(),
    )

    try:
        dataset.name = "other"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_training_dataset_basic():
    """TrainingDataset stores name, version, and splits."""
    train_ex = TrainingExample(messages=(ChatMessage(role="user", content="Train"),))
    valid_ex = TrainingExample(messages=(ChatMessage(role="user", content="Valid"),))
    test_ex = TrainingExample(messages=(ChatMessage(role="user", content="Test"),))

    dataset = TrainingDataset(
        name="my-dataset",
        version="2026-02-11",
        train=(train_ex,),
        valid=(valid_ex,),
        test=(test_ex,),
    )

    assert dataset.name == "my-dataset"
    assert dataset.version == "2026-02-11"
    assert len(dataset.train) == 1
    assert len(dataset.valid) == 1
    assert len(dataset.test) == 1


def test_training_dataset_empty_splits():
    """TrainingDataset allows empty splits."""
    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(),
        valid=(),
        test=(),
    )

    assert len(dataset.train) == 0
    assert len(dataset.valid) == 0
    assert len(dataset.test) == 0


def test_dataset_stats_frozen():
    """DatasetStats instances are immutable."""
    stats = DatasetStats(
        total_examples=100,
        train_count=80,
        valid_count=10,
        test_count=10,
        avg_messages_per_example=3.5,
    )

    try:
        stats.total_examples = 200  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_dataset_stats_basic():
    """DatasetStats stores all fields."""
    stats = DatasetStats(
        total_examples=100,
        train_count=80,
        valid_count=10,
        test_count=10,
        avg_messages_per_example=3.5,
    )

    assert stats.total_examples == 100
    assert stats.train_count == 80
    assert stats.valid_count == 10
    assert stats.test_count == 10
    assert stats.avg_messages_per_example == 3.5
    assert stats.categories is None


def test_dataset_stats_with_categories():
    """DatasetStats can include category breakdown."""
    stats = DatasetStats(
        total_examples=100,
        train_count=80,
        valid_count=10,
        test_count=10,
        avg_messages_per_example=3.5,
        categories={"tool_calling": 40, "code_generation": 60},
    )

    assert stats.categories == {"tool_calling": 40, "code_generation": 60}
