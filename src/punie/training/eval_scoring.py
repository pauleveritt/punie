"""Scoring functions for evaluation results."""

from punie.training.eval_prompts import EvalPrompt


def score_tool_calling(
    prompt: EvalPrompt,
    response: str,
    tool_calls: tuple[str, ...],
) -> float:
    """Score tool calling accuracy.

    Computes the fraction of expected tools that were actually called.

    Args:
        prompt: The evaluation prompt with expected_tool_calls
        response: Model's response text (unused, but kept for consistency)
        tool_calls: Names of tools that were actually called

    Returns:
        Score from 0.0 to 1.0 (1.0 = all expected tools called)
    """
    if not prompt.expected_tool_calls:
        # No tools expected - perfect score if no tools called
        return 1.0 if not tool_calls else 0.5

    # Calculate fraction of expected tools that were called
    expected_set = set(prompt.expected_tool_calls)
    called_set = set(tool_calls)
    matched = expected_set & called_set

    return len(matched) / len(expected_set)


def score_keyword_presence(prompt: EvalPrompt, response: str) -> float:
    """Score keyword presence in response.

    Computes the fraction of expected keywords found in the response.

    Args:
        prompt: The evaluation prompt with expected_keywords
        response: Model's response text

    Returns:
        Score from 0.0 to 1.0 (1.0 = all keywords present)
    """
    if not prompt.expected_keywords:
        # No keywords expected - perfect score
        return 1.0

    # Case-insensitive keyword matching
    response_lower = response.lower()
    found = sum(1 for keyword in prompt.expected_keywords if keyword.lower() in response_lower)

    return found / len(prompt.expected_keywords)


def score_prompt(
    prompt: EvalPrompt,
    response: str,
    tool_calls: tuple[str, ...],
) -> float:
    """Compute combined score for a prompt.

    Combines tool calling score and keyword presence score.
    If both are applicable, returns average. Otherwise returns whichever is applicable.

    Args:
        prompt: The evaluation prompt
        response: Model's response text
        tool_calls: Names of tools that were called

    Returns:
        Combined score from 0.0 to 1.0
    """
    tool_score = score_tool_calling(prompt, response, tool_calls)
    keyword_score = score_keyword_presence(prompt, response)

    # If both have expectations, average them
    has_tool_expectations = bool(prompt.expected_tool_calls)
    has_keyword_expectations = bool(prompt.expected_keywords)

    if has_tool_expectations and has_keyword_expectations:
        return (tool_score + keyword_score) / 2.0
    elif has_tool_expectations:
        return tool_score
    elif has_keyword_expectations:
        return keyword_score
    else:
        # No expectations - perfect score (prompt is just for qualitative evaluation)
        return 1.0
