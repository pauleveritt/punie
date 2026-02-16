"""Tests for prompt_utils module.

Tests that format_prompt() produces correct ChatML format and matches
the tokenizer's output, ensuring train/test consistency.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from punie.agent.prompt_utils import (
    clear_tokenizer_cache,
    extract_python_from_code_mode,
    extract_tool_calls_from_response,
    format_prompt,
    format_prompt_with_history,
    get_tokenizer,
    is_tool_response,
    validate_python_code,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear tokenizer cache before each test."""
    clear_tokenizer_cache()
    yield
    clear_tokenizer_cache()


def test_format_prompt_produces_chatml_format():
    """Test that format_prompt produces correct ChatML format."""
    # Mock the tokenizer
    mock_tokenizer = Mock()
    mock_tokenizer.apply_chat_template.return_value = (
        "<|im_start|>system\n"
        "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        "<|im_start|>user\n"
        "Check types in src/<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
        prompt = format_prompt("Check types in src/", "test_model")

        # Should contain required ChatML tokens
        assert "<|im_start|>system" in prompt
        assert "<|im_end|>" in prompt
        assert "<|im_start|>user" in prompt
        assert "<|im_start|>assistant" in prompt

        # Should contain the query
        assert "Check types in src/" in prompt

        # Should contain default system message
        assert "Punie" in prompt


def test_format_prompt_uses_tokenizer_apply_chat_template():
    """Test that format_prompt uses tokenizer.apply_chat_template()."""
    mock_tokenizer = Mock()
    mock_tokenizer.apply_chat_template.return_value = "formatted_prompt"

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
        prompt = format_prompt("Test query", "test_model")

        # Should call apply_chat_template with correct arguments
        mock_tokenizer.apply_chat_template.assert_called_once()
        call_args = mock_tokenizer.apply_chat_template.call_args

        # Check messages format
        messages = call_args[0][0]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Test query"

        # Check keyword arguments
        assert call_args[1]["tokenize"] is False
        assert call_args[1]["add_generation_prompt"] is True


def test_format_prompt_with_custom_system_message():
    """Test format_prompt with custom system message."""
    mock_tokenizer = Mock()
    mock_tokenizer.apply_chat_template.return_value = "formatted_prompt"

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
        custom_system = "Custom system message"
        format_prompt("Test query", "test_model", system_message=custom_system)

        # Should use custom system message
        call_args = mock_tokenizer.apply_chat_template.call_args
        messages = call_args[0][0]
        assert messages[0]["content"] == custom_system


def test_format_prompt_with_history():
    """Test format_prompt_with_history includes conversation history."""
    mock_tokenizer = Mock()
    mock_tokenizer.apply_chat_template.return_value = "formatted_prompt"

    history = [
        {"role": "user", "content": "What is DI?"},
        {"role": "assistant", "content": "Dependency injection is..."},
    ]

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
        format_prompt_with_history("Show me an example", "test_model", history=history)

        # Should include system + history + new query
        call_args = mock_tokenizer.apply_chat_template.call_args
        messages = call_args[0][0]

        assert len(messages) == 4  # system + 2 history + new query
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "What is DI?"}
        assert messages[2] == {"role": "assistant", "content": "Dependency injection is..."}
        assert messages[3] == {"role": "user", "content": "Show me an example"}


def test_get_tokenizer_caches():
    """Test that get_tokenizer caches tokenizers."""
    mock_tokenizer = Mock()

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer) as mock_from_pretrained:
        # First call should load
        tok1 = get_tokenizer("test_model")
        assert mock_from_pretrained.call_count == 1

        # Second call should use cache
        tok2 = get_tokenizer("test_model")
        assert mock_from_pretrained.call_count == 1  # Still 1, not 2

        # Should return same instance
        assert tok1 is tok2


def test_clear_tokenizer_cache():
    """Test that clear_tokenizer_cache clears the cache."""
    mock_tokenizer = Mock()

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer) as mock_from_pretrained:
        # Load tokenizer
        get_tokenizer("test_model")
        assert mock_from_pretrained.call_count == 1

        # Clear cache
        clear_tokenizer_cache()

        # Next call should reload
        get_tokenizer("test_model")
        assert mock_from_pretrained.call_count == 2


def test_format_prompt_does_not_use_manual_formatting():
    """Test that format_prompt doesn't use f-strings or manual concatenation.

    This test ensures we're actually using the tokenizer API, not manual formatting.
    Phase 26.1 lesson learned: Manual formatting causes train/test mismatch.
    """
    mock_tokenizer = Mock()
    mock_tokenizer.apply_chat_template.return_value = "tokenizer_output"

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
        prompt = format_prompt("Test query", "test_model")

        # Should return tokenizer's output, not manually formatted string
        assert prompt == "tokenizer_output"
        assert prompt != "User: Test query\nAssistant:"  # Wrong format!


def test_format_prompt_handles_pathlib_path():
    """Test that format_prompt accepts pathlib.Path for model_path."""
    mock_tokenizer = Mock()
    mock_tokenizer.apply_chat_template.return_value = "formatted_prompt"

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
        # Should accept both str and Path
        prompt1 = format_prompt("Test", "test_model")
        prompt2 = format_prompt("Test", Path("test_model"))

        assert prompt1 == prompt2


def test_format_prompt_prevents_catastrophic_failure():
    """Integration test: Ensure format_prompt prevents Phase 26 bug.

    Phase 26.1 lesson learned: Using plain text prompt ("User: {query}\\nAssistant:")
    instead of ChatML caused 60-point accuracy drop (28% → 88%).

    This test verifies that our utility prevents this class of bug.
    """
    mock_tokenizer = Mock()
    mock_tokenizer.apply_chat_template.return_value = (
        "<|im_start|>system\n"
        "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        "<|im_start|>user\n"
        "Check types in src/<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    with patch("punie.agent.prompt_utils.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
        prompt = format_prompt("Check types in src/", "test_model")

        # MUST NOT produce plain text format (this caused the bug)
        assert not prompt.startswith("User:")
        assert "Assistant:" not in prompt or "<|im_start|>assistant" in prompt

        # MUST produce ChatML format
        assert "<|im_start|>" in prompt
        assert "<|im_end|>" in prompt


# Mark as slow since it requires model files (optional, can be skipped)
@pytest.mark.slow
def test_format_prompt_with_real_model(tmp_path):
    """Test format_prompt with a real model (if available).

    This test is marked as slow and will be skipped unless --run-slow is passed.
    It's useful for verifying the integration with real models.
    """
    # This test requires a real model directory
    # Skip if model doesn't exist
    model_path = Path("fused_model_qwen3_phase27_augmented_5bit")
    if not model_path.exists():
        pytest.skip("Model not found - skipping integration test")

    # Should not raise any errors
    prompt = format_prompt("Check types in src/", model_path)

    # Should produce valid ChatML format
    assert "<|im_start|>" in prompt
    assert "<|im_end|>" in prompt
    assert "Check types in src/" in prompt


def test_extract_tool_calls_from_response():
    """Test extracting tool calls from model response."""
    # Test <tool_call> format
    response = "<tool_call>result = typecheck('src/')</tool_call>"
    calls = extract_tool_calls_from_response(response)
    assert len(calls) == 1
    assert calls[0] == "result = typecheck('src/')"

    # Test multiple tool calls
    response = """
    <tool_call>result = typecheck('src/')</tool_call>
    Some explanation
    <tool_call>ruff_result = ruff_check('src/')</tool_call>
    """
    calls = extract_tool_calls_from_response(response)
    assert len(calls) == 2
    assert "typecheck" in calls[0]
    assert "ruff_check" in calls[1]

    # Test direct answer (no tool calls)
    response = "Dependency injection is a design pattern..."
    calls = extract_tool_calls_from_response(response)
    assert len(calls) == 0


def test_extract_python_from_code_mode():
    """Test extracting Python from Code Mode XML wrapper."""
    # Test with full XML wrapper
    raw = '<function=execute_code><parameter=code>result = typecheck("src/")</parameter></function>'
    python = extract_python_from_code_mode(raw)
    assert python == 'result = typecheck("src/")'

    # Test with already clean Python
    raw = 'result = typecheck("src/")'
    python = extract_python_from_code_mode(raw)
    assert python == 'result = typecheck("src/")'

    # Test with multiline Python
    raw = """<parameter=code>
result = typecheck("src/")
if result.error_count > 0:
    print(f"Found {result.error_count} errors")
</parameter>"""
    python = extract_python_from_code_mode(raw)
    assert 'result = typecheck("src/")' in python
    assert "if result.error_count > 0:" in python

    # Test with no valid Python
    raw = "<function=execute_code><parameter=data>invalid</parameter></function>"
    python = extract_python_from_code_mode(raw)
    assert python is None


def test_is_tool_response():
    """Test detecting tool call vs direct answer."""
    # Tool call formats
    assert is_tool_response("<tool_call>result = typecheck('src/')</tool_call>")
    assert is_tool_response("```python\nexecute_code(...)\n```")
    assert is_tool_response("```json\n{...}\n```")

    # Direct answers
    assert not is_tool_response("Dependency injection is a design pattern...")
    assert not is_tool_response("You should use Protocol when...")
    assert not is_tool_response("The difference between merge and rebase is...")


def test_validate_python_code():
    """Test Python code validation using AST."""
    # Valid code
    is_valid, error = validate_python_code("x = 1 + 2")
    assert is_valid
    assert error is None

    is_valid, error = validate_python_code("result = typecheck('src/')")
    assert is_valid
    assert error is None

    # Invalid code
    is_valid, error = validate_python_code("x = 1 +")
    assert not is_valid
    assert "SyntaxError" in error

    is_valid, error = validate_python_code("if True\n    print('hi')")
    assert not is_valid
    assert "SyntaxError" in error
