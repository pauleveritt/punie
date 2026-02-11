"""Tests for pre-defined evaluation suites."""

from punie.training.eval_suites import create_baseline_suite


def test_create_baseline_suite():
    """create_baseline_suite returns a valid EvalSuite."""
    suite = create_baseline_suite()

    assert suite.name == "baseline"
    assert len(suite.prompts) > 0


def test_baseline_suite_has_all_categories():
    """Baseline suite includes all three categories."""
    suite = create_baseline_suite()

    tool_prompts = suite.by_category("tool_calling")
    code_prompts = suite.by_category("code_generation")
    reasoning_prompts = suite.by_category("reasoning")

    assert len(tool_prompts) > 0, "Should have tool_calling prompts"
    assert len(code_prompts) > 0, "Should have code_generation prompts"
    assert len(reasoning_prompts) > 0, "Should have reasoning prompts"


def test_baseline_suite_unique_ids():
    """Baseline suite prompts have unique IDs."""
    suite = create_baseline_suite()

    ids = [p.id for p in suite.prompts]
    assert len(ids) == len(set(ids)), "All prompt IDs should be unique"


def test_baseline_suite_tool_calling_has_expectations():
    """Tool calling prompts specify expected tool calls."""
    suite = create_baseline_suite()
    tool_prompts = suite.by_category("tool_calling")

    for prompt in tool_prompts:
        assert len(prompt.expected_tool_calls) > 0, f"Prompt {prompt.id} should expect tool calls"


def test_baseline_suite_code_generation_has_keywords():
    """Code generation prompts specify expected keywords."""
    suite = create_baseline_suite()
    code_prompts = suite.by_category("code_generation")

    for prompt in code_prompts:
        assert len(prompt.expected_keywords) > 0, f"Prompt {prompt.id} should expect keywords"
