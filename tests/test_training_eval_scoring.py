"""Tests for evaluation scoring functions."""

from punie.training.eval_prompts import EvalPrompt
from punie.training.eval_scoring import score_keyword_presence, score_prompt, score_tool_calling


def test_score_tool_calling_perfect():
    """score_tool_calling returns 1.0 when all tools called."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test",
        expected_tool_calls=("read_file", "write_file"),
    )

    score = score_tool_calling(prompt, "response", ("read_file", "write_file"))
    assert score == 1.0


def test_score_tool_calling_partial():
    """score_tool_calling returns fraction when some tools called."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test",
        expected_tool_calls=("read_file", "write_file", "run_command"),
    )

    score = score_tool_calling(prompt, "response", ("read_file", "write_file"))
    assert score == 2.0 / 3.0


def test_score_tool_calling_none():
    """score_tool_calling returns 0.0 when no expected tools called."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test",
        expected_tool_calls=("read_file", "write_file"),
    )

    score = score_tool_calling(prompt, "response", ())
    assert score == 0.0


def test_score_tool_calling_extra():
    """score_tool_calling ignores extra tool calls."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test",
        expected_tool_calls=("read_file",),
    )

    score = score_tool_calling(prompt, "response", ("read_file", "write_file", "run_command"))
    assert score == 1.0  # Got the expected one, extras don't hurt


def test_score_tool_calling_no_expectations():
    """score_tool_calling returns 1.0 when no tools expected and none called."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
    )

    score = score_tool_calling(prompt, "response", ())
    assert score == 1.0


def test_score_tool_calling_no_expectations_but_called():
    """score_tool_calling returns 0.5 when no tools expected but some called."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
    )

    score = score_tool_calling(prompt, "response", ("read_file",))
    assert score == 0.5  # Penalty for calling unexpected tools


def test_score_keyword_presence_perfect():
    """score_keyword_presence returns 1.0 when all keywords present."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
        expected_keywords=("def", "return"),
    )

    response = "def factorial(n):\n    return n"
    score = score_keyword_presence(prompt, response)
    assert score == 1.0


def test_score_keyword_presence_partial():
    """score_keyword_presence returns fraction when some keywords present."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
        expected_keywords=("def", "return", "recursive"),
    )

    response = "def factorial(n):\n    return n"
    score = score_keyword_presence(prompt, response)
    assert score == 2.0 / 3.0  # "def" and "return" present, "recursive" missing


def test_score_keyword_presence_none():
    """score_keyword_presence returns 0.0 when no keywords present."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
        expected_keywords=("def", "return"),
    )

    response = "This is some text without the expected keywords"
    score = score_keyword_presence(prompt, response)
    assert score == 0.0


def test_score_keyword_presence_case_insensitive():
    """score_keyword_presence is case-insensitive."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
        expected_keywords=("DEF", "RETURN"),
    )

    response = "def factorial(n):\n    return n"
    score = score_keyword_presence(prompt, response)
    assert score == 1.0


def test_score_keyword_presence_no_expectations():
    """score_keyword_presence returns 1.0 when no keywords expected."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
    )

    response = "Any response"
    score = score_keyword_presence(prompt, response)
    assert score == 1.0


def test_score_prompt_tool_only():
    """score_prompt uses tool score when only tools expected."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test",
        expected_tool_calls=("read_file",),
    )

    score = score_prompt(prompt, "response", ("read_file",))
    assert score == 1.0


def test_score_prompt_keyword_only():
    """score_prompt uses keyword score when only keywords expected."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Test",
        expected_keywords=("def", "return"),
    )

    response = "def foo():\n    return 1"
    score = score_prompt(prompt, response, ())
    assert score == 1.0


def test_score_prompt_both():
    """score_prompt averages when both tools and keywords expected."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test",
        expected_tool_calls=("read_file",),
        expected_keywords=("content", "file"),
    )

    response = "I read the content from the file"
    tool_calls = ("read_file",)

    score = score_prompt(prompt, response, tool_calls)
    assert score == 1.0  # Both perfect


def test_score_prompt_both_partial():
    """score_prompt averages partial scores."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test",
        expected_tool_calls=("read_file", "write_file"),
        expected_keywords=("content", "file"),
    )

    response = "I got the content"  # Only 1 of 2 keywords
    tool_calls = ("read_file",)  # Only 1 of 2 tools

    score = score_prompt(prompt, response, tool_calls)
    assert score == 0.5  # Average of 0.5 and 0.5


def test_score_prompt_no_expectations():
    """score_prompt returns 1.0 when no expectations (qualitative only)."""
    prompt = EvalPrompt(
        id="test-01",
        category="reasoning",
        prompt_text="Explain something",
    )

    score = score_prompt(prompt, "Some explanation", ())
    assert score == 1.0
