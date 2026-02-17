"""Tests for training dataset: dataclasses, filtering, I/O, and validation.

Consolidates:
- Dataset dataclasses (ChatMessage, TrainingExample, TrainingDataset, DatasetStats)
- Dataset filtering (language, Python version, content quality)
- Dataset I/O (JSONL read/write, dataset read/write)
- Dataset validation (example and dataset validation)
"""

from __future__ import annotations

from pathlib import Path


from punie.training.dataset import ChatMessage, DatasetStats, TrainingDataset, TrainingExample
from punie.training.dataset_filters import (
    filter_by_content_quality,
    filter_by_language,
    filter_by_python_version,
)
from punie.training.dataset_io import (
    compute_stats,
    read_dataset,
    read_jsonl,
    write_dataset,
    write_jsonl,
)
from punie.training.dataset_validation import validate_dataset, validate_example


# ============================================================================
# Dataset Dataclasses Tests
# ============================================================================


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


# ============================================================================
# Dataset Filtering Tests
# ============================================================================


def test_filter_by_language_english():
    """English examples are kept."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Hello, how are you?"),
            ChatMessage(role="assistant", content="I'm doing well, thanks!"),
        )
    )

    kept, removed = filter_by_language((example,), language="en")
    assert len(kept) == 1
    assert len(removed) == 0


def test_filter_by_language_chinese():
    """Chinese examples are removed."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="你好吗？"),
            ChatMessage(role="assistant", content="我很好，谢谢！"),
        )
    )

    kept, removed = filter_by_language((example,), language="en")
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_language_mixed():
    """Mixed language examples are removed."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Hello 你好"),
            ChatMessage(role="assistant", content="Hi there!"),
        )
    )

    kept, removed = filter_by_language((example,), language="en")
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_python_version_modern():
    """Modern Python code is kept."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Write a function"),
            ChatMessage(role="assistant", content="def add(a: int, b: int) -> int:\n    return a + b"),
        )
    )

    kept, removed = filter_by_python_version((example,))
    assert len(kept) == 1
    assert len(removed) == 0


def test_filter_by_python_version_print_statement():
    """Python 2 print statement is removed."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Print hello"),
            ChatMessage(role="assistant", content="print 'hello'"),  # Python 2 syntax
        )
    )

    kept, removed = filter_by_python_version((example,))
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_python_version_has_key():
    """Python 2 dict.has_key() is removed."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Check if key exists"),
            ChatMessage(role="assistant", content="if mydict.has_key('foo'):"),
        )
    )

    kept, removed = filter_by_python_version((example,))
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_python_version_xrange():
    """Python 2 xrange is removed."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Loop"),
            ChatMessage(role="assistant", content="for i in xrange(10):"),
        )
    )

    kept, removed = filter_by_python_version((example,))
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_python_version_print_function():
    """Python 3 print function is kept."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Print hello"),
            ChatMessage(role="assistant", content="print('hello')"),  # Python 3 syntax
        )
    )

    kept, removed = filter_by_python_version((example,))
    assert len(kept) == 1
    assert len(removed) == 0


def test_filter_by_content_quality_valid():
    """High quality example is kept."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="This is a good question about programming"),
            ChatMessage(role="assistant", content="Here is a detailed answer with code examples"),
        )
    )

    kept, removed = filter_by_content_quality((example,))
    assert len(kept) == 1
    assert len(removed) == 0


def test_filter_by_content_quality_too_few_messages():
    """Example with too few messages is removed."""
    example = TrainingExample(
        messages=(ChatMessage(role="user", content="Hello there everyone"),)
    )

    kept, removed = filter_by_content_quality((example,), min_messages=2)
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_content_quality_short_content():
    """Example with very short content is removed."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Hi"),  # Too short
            ChatMessage(role="assistant", content="Hello"),  # Too short
        )
    )

    kept, removed = filter_by_content_quality((example,))
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_content_quality_last_not_assistant():
    """Example where last message isn't assistant is removed."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="This is a longer question"),
            ChatMessage(role="user", content="And another question follows"),
        )
    )

    kept, removed = filter_by_content_quality((example,))
    assert len(kept) == 0
    assert len(removed) == 1


def test_filter_by_content_quality_adequate_length():
    """Example with adequate content length is kept."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Question here"),  # 13 chars
            ChatMessage(role="assistant", content="Answer here!"),  # 12 chars
        )
    )

    kept, removed = filter_by_content_quality((example,))
    assert len(kept) == 1
    assert len(removed) == 0


def test_filters_return_tuples():
    """All filters return tuples (not lists)."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Test question here"),
            ChatMessage(role="assistant", content="Test answer here"),
        )
    )

    kept, removed = filter_by_language((example,))
    assert isinstance(kept, tuple)
    assert isinstance(removed, tuple)

    kept, removed = filter_by_python_version((example,))
    assert isinstance(kept, tuple)
    assert isinstance(removed, tuple)

    kept, removed = filter_by_content_quality((example,))
    assert isinstance(kept, tuple)
    assert isinstance(removed, tuple)


# ============================================================================
# Dataset I/O Tests
# ============================================================================


def test_write_jsonl(tmp_path: Path):
    """write_jsonl creates valid JSONL file."""
    examples = (
        TrainingExample(
            messages=(
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi!"),
            )
        ),
        TrainingExample(
            messages=(
                ChatMessage(role="user", content="Bye"),
                ChatMessage(role="assistant", content="Goodbye!"),
            )
        ),
    )

    output_file = tmp_path / "test.jsonl"
    write_jsonl(examples, output_file)

    assert output_file.exists()

    # Verify content
    lines = output_file.read_text().strip().split("\n")
    assert len(lines) == 2


def test_read_jsonl(tmp_path: Path):
    """read_jsonl reads JSONL file correctly."""
    # Write test data
    content = """{"messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]}
{"messages": [{"role": "user", "content": "Bye"}, {"role": "assistant", "content": "Goodbye!"}]}
"""
    file_path = tmp_path / "test.jsonl"
    file_path.write_text(content)

    # Read it back
    examples = read_jsonl(file_path)

    assert len(examples) == 2
    assert examples[0].messages[0].content == "Hello"
    assert examples[1].messages[0].content == "Bye"


def test_write_read_roundtrip(tmp_path: Path):
    """Write and read produce identical data."""
    original = (
        TrainingExample(
            messages=(
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="What is 2+2?"),
                ChatMessage(role="assistant", content="4"),
            )
        ),
    )

    file_path = tmp_path / "roundtrip.jsonl"
    write_jsonl(original, file_path)
    restored = read_jsonl(file_path)

    assert len(restored) == len(original)
    assert restored[0].messages == original[0].messages


def test_write_dataset(tmp_path: Path):
    """write_dataset creates directory and split files."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Test"),
            ChatMessage(role="assistant", content="Response"),
        )
    )

    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(example,),
        valid=(example,),
        test=(),
    )

    output_dir = tmp_path / "dataset"
    write_dataset(dataset, output_dir)

    assert output_dir.exists()
    assert (output_dir / "train.jsonl").exists()
    assert (output_dir / "valid.jsonl").exists()
    assert (output_dir / "test.jsonl").exists()


def test_read_dataset(tmp_path: Path):
    """read_dataset reads all splits correctly."""
    # Create test files
    output_dir = tmp_path / "dataset"
    output_dir.mkdir()

    train_content = '{"messages": [{"role": "user", "content": "Train"}, {"role": "assistant", "content": "Response"}]}\n'
    (output_dir / "train.jsonl").write_text(train_content)

    valid_content = '{"messages": [{"role": "user", "content": "Valid"}, {"role": "assistant", "content": "Response"}]}\n'
    (output_dir / "valid.jsonl").write_text(valid_content)

    (output_dir / "test.jsonl").write_text("")  # Empty test split

    # Read dataset
    dataset = read_dataset(output_dir, name="my-dataset", version="2.0")

    assert dataset.name == "my-dataset"
    assert dataset.version == "2.0"
    assert len(dataset.train) == 1
    assert len(dataset.valid) == 1
    assert len(dataset.test) == 0
    assert dataset.train[0].messages[0].content == "Train"


def test_write_read_dataset_roundtrip(tmp_path: Path):
    """Write and read dataset produce identical data."""
    example1 = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Question 1"),
            ChatMessage(role="assistant", content="Answer 1"),
        )
    )
    example2 = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Question 2"),
            ChatMessage(role="assistant", content="Answer 2"),
        )
    )

    original = TrainingDataset(
        name="test",
        version="1.0",
        train=(example1,),
        valid=(example2,),
        test=(),
    )

    output_dir = tmp_path / "roundtrip"
    write_dataset(original, output_dir)
    restored = read_dataset(output_dir, name="test", version="1.0")

    assert restored.name == original.name
    assert restored.version == original.version
    assert len(restored.train) == len(original.train)
    assert len(restored.valid) == len(original.valid)
    assert restored.train[0].messages == original.train[0].messages


def test_compute_stats():
    """compute_stats calculates correct statistics."""
    examples = [
        TrainingExample(
            messages=(
                ChatMessage(role="user", content="Q"),
                ChatMessage(role="assistant", content="A"),
            )
        ),
        TrainingExample(
            messages=(
                ChatMessage(role="system", content="S"),
                ChatMessage(role="user", content="Q"),
                ChatMessage(role="assistant", content="A"),
            )
        ),
    ]

    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=tuple(examples[:1]),
        valid=tuple(examples[1:]),
        test=(),
    )

    stats = compute_stats(dataset)

    assert stats.total_examples == 2
    assert stats.train_count == 1
    assert stats.valid_count == 1
    assert stats.test_count == 0
    assert stats.avg_messages_per_example == 2.5  # (2 + 3) / 2


def test_compute_stats_empty():
    """compute_stats handles empty dataset."""
    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(),
        valid=(),
        test=(),
    )

    stats = compute_stats(dataset)

    assert stats.total_examples == 0
    assert stats.avg_messages_per_example == 0.0


def test_read_jsonl_empty_lines(tmp_path: Path):
    """read_jsonl skips empty lines."""
    content = """{"messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]}

{"messages": [{"role": "user", "content": "Bye"}, {"role": "assistant", "content": "Goodbye!"}]}
"""
    file_path = tmp_path / "test.jsonl"
    file_path.write_text(content)

    examples = read_jsonl(file_path)

    assert len(examples) == 2


# ============================================================================
# Dataset Validation Tests
# ============================================================================


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
