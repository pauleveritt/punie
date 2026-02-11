"""Tests for dataset filtering functions."""

from punie.training.dataset import ChatMessage, TrainingExample
from punie.training.dataset_filters import (
    filter_by_content_quality,
    filter_by_language,
    filter_by_python_version,
)


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
