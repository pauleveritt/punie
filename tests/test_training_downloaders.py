"""Tests for dataset downloaders.

Note: These tests use mock data to avoid downloading actual datasets.
Integration tests would download real data but are marked slow.
"""

from punie.training.downloaders import _convert_to_chat_format


def test_convert_to_chat_format_text():
    """_convert_to_chat_format converts text to chat messages."""
    text = "This is some sample text content."

    messages = _convert_to_chat_format(text, is_code=False)

    assert len(messages) == 3
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert messages[2].role == "assistant"
    assert messages[2].content == text


def test_convert_to_chat_format_code():
    """_convert_to_chat_format handles code content."""
    code = "def add(a, b):\n    return a + b"

    messages = _convert_to_chat_format(code, is_code=True)

    assert len(messages) == 3
    assert "coding" in messages[0].content.lower()
    assert messages[2].content == code


def test_convert_to_chat_format_system_message():
    """_convert_to_chat_format includes appropriate system message."""
    text = "Sample content"

    messages_text = _convert_to_chat_format(text, is_code=False)
    messages_code = _convert_to_chat_format(text, is_code=True)

    assert "assistant" in messages_text[0].content.lower()
    assert "coding" in messages_code[0].content.lower()


# Integration tests (require actual dataset download - mark as slow)
# These are commented out to avoid slow downloads during normal testing
# Uncomment to test with real datasets

# import pytest
# from pathlib import Path
#
# @pytest.mark.slow
# def test_download_sample_dataset(tmp_path: Path):
#     """Integration test: download sample dataset."""
#     from punie.training.downloaders import download_sample_dataset
#
#     output_dir = tmp_path / "sample"
#     stats = download_sample_dataset(output_dir, max_examples=10)
#
#     assert stats.total_examples > 0
#     assert (output_dir / "train.jsonl").exists()
#     assert (output_dir / "valid.jsonl").exists()
#     assert (output_dir / "test.jsonl").exists()
