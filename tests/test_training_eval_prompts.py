"""Tests for evaluation prompt dataclasses."""

import pytest

from punie.training.eval_prompts import EvalPrompt, EvalSuite


def test_eval_prompt_frozen():
    """EvalPrompt instances are immutable."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Test prompt",
    )

    try:
        prompt.id = "test-02"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_eval_prompt_defaults():
    """EvalPrompt has sensible defaults."""
    prompt = EvalPrompt(
        id="test-01",
        category="code_generation",
        prompt_text="Write a function",
    )

    assert prompt.id == "test-01"
    assert prompt.category == "code_generation"
    assert prompt.prompt_text == "Write a function"
    assert prompt.expected_tool_calls == ()
    assert prompt.expected_keywords == ()


def test_eval_prompt_with_expectations():
    """EvalPrompt can specify expected outputs."""
    prompt = EvalPrompt(
        id="test-01",
        category="tool_calling",
        prompt_text="Read file.txt",
        expected_tool_calls=("read_file",),
        expected_keywords=("file.txt", "content"),
    )

    assert prompt.expected_tool_calls == ("read_file",)
    assert prompt.expected_keywords == ("file.txt", "content")


def test_eval_suite_frozen():
    """EvalSuite instances are immutable."""
    prompt = EvalPrompt(id="test-01", category="test", prompt_text="Test")
    suite = EvalSuite(name="test-suite", prompts=(prompt,))

    try:
        suite.name = "other-suite"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_eval_suite_basic():
    """EvalSuite stores prompts."""
    prompt1 = EvalPrompt(id="test-01", category="test", prompt_text="Test 1")
    prompt2 = EvalPrompt(id="test-02", category="test", prompt_text="Test 2")
    suite = EvalSuite(name="test-suite", prompts=(prompt1, prompt2))

    assert suite.name == "test-suite"
    assert len(suite.prompts) == 2
    assert suite.prompts[0] == prompt1
    assert suite.prompts[1] == prompt2


def test_eval_suite_by_category():
    """EvalSuite.by_category() filters prompts."""
    prompt1 = EvalPrompt(id="tool-01", category="tool_calling", prompt_text="Use tool")
    prompt2 = EvalPrompt(id="code-01", category="code_generation", prompt_text="Write code")
    prompt3 = EvalPrompt(id="tool-02", category="tool_calling", prompt_text="Another tool")
    suite = EvalSuite(name="test-suite", prompts=(prompt1, prompt2, prompt3))

    tool_prompts = suite.by_category("tool_calling")
    assert len(tool_prompts) == 2
    assert tool_prompts[0] == prompt1
    assert tool_prompts[1] == prompt3

    code_prompts = suite.by_category("code_generation")
    assert len(code_prompts) == 1
    assert code_prompts[0] == prompt2


def test_eval_suite_by_category_empty():
    """EvalSuite.by_category() returns empty tuple if no matches."""
    prompt = EvalPrompt(id="test-01", category="tool_calling", prompt_text="Test")
    suite = EvalSuite(name="test-suite", prompts=(prompt,))

    reasoning_prompts = suite.by_category("reasoning")
    assert reasoning_prompts == ()


def test_eval_suite_unique_ids():
    """EvalSuite prompts should have unique IDs (convention, not enforced)."""
    prompt1 = EvalPrompt(id="test-01", category="test", prompt_text="Test 1")
    prompt2 = EvalPrompt(id="test-02", category="test", prompt_text="Test 2")
    suite = EvalSuite(name="test-suite", prompts=(prompt1, prompt2))

    ids = [p.id for p in suite.prompts]
    assert len(ids) == len(set(ids)), "IDs should be unique"
