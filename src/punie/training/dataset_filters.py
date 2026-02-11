"""Dataset filtering functions for progressive pruning.

Each filter function returns (kept, removed) tuples so we can inspect
what was filtered out at each step.
"""

import re

from punie.training.dataset import TrainingExample


def filter_by_language(
    examples: tuple[TrainingExample, ...],
    language: str = "en",
) -> tuple[tuple[TrainingExample, ...], tuple[TrainingExample, ...]]:
    """Filter examples by language (simple heuristic).

    Currently only supports English detection via basic patterns.
    This is a simple heuristic - not perfect but catches obvious cases.

    Args:
        examples: Examples to filter
        language: Language code (only "en" supported currently)

    Returns:
        (kept_examples, removed_examples) tuple
    """
    if language != "en":
        # For now, only English filtering is implemented
        return examples, ()

    kept = []
    removed = []

    # Simple English detection heuristics
    non_english_patterns = [
        r"[\u4e00-\u9fff]",  # Chinese characters
        r"[\u3040-\u309f\u30a0-\u30ff]",  # Japanese hiragana/katakana
        r"[\u0400-\u04ff]",  # Cyrillic
        r"[\u0600-\u06ff]",  # Arabic
    ]

    for example in examples:
        # Check all message content
        is_english = True
        for msg in example.messages:
            for pattern in non_english_patterns:
                if re.search(pattern, msg.content):
                    is_english = False
                    break
            if not is_english:
                break

        if is_english:
            kept.append(example)
        else:
            removed.append(example)

    return tuple(kept), tuple(removed)


def filter_by_python_version(
    examples: tuple[TrainingExample, ...],
    min_version: str = "3.10",
) -> tuple[tuple[TrainingExample, ...], tuple[TrainingExample, ...]]:
    """Filter out examples with old Python code patterns.

    Removes code using Python 2 or very old Python 3 features.

    Args:
        examples: Examples to filter
        min_version: Minimum Python version (e.g., "3.10", "3", "3.8")

    Returns:
        (kept_examples, removed_examples) tuple
    """
    kept = []
    removed = []

    # Python 2 / old Python patterns to detect
    old_patterns = [
        r"\bprint\s+[^(]",  # print statement without parens
        r"\.has_key\(",  # dict.has_key() (removed in Python 3)
        r"\bxrange\b",  # xrange (Python 2)
        r"<>\s",  # <> comparison operator (Python 2)
        r"^class\s+\w+:",  # Old-style class without (object)
        r"\bexecfile\b",  # execfile (Python 2)
        r"\bunicode\b",  # unicode type (Python 2)
        r"from\s+__future__",  # __future__ imports (usually Python 2 compat)
    ]

    for example in examples:
        is_modern = True

        # Check all message content for old patterns
        for msg in example.messages:
            for pattern in old_patterns:
                if re.search(pattern, msg.content, re.MULTILINE):
                    is_modern = False
                    break
            if not is_modern:
                break

        if is_modern:
            kept.append(example)
        else:
            removed.append(example)

    return tuple(kept), tuple(removed)


def filter_by_content_quality(
    examples: tuple[TrainingExample, ...],
    min_messages: int = 2,
) -> tuple[tuple[TrainingExample, ...], tuple[TrainingExample, ...]]:
    """Filter examples by content quality heuristics.

    Removes malformed or too-short examples.

    Args:
        examples: Examples to filter
        min_messages: Minimum number of messages required

    Returns:
        (kept_examples, removed_examples) tuple
    """
    kept = []
    removed = []

    for example in examples:
        is_quality = True

        # Must have minimum number of messages
        if len(example.messages) < min_messages:
            is_quality = False

        # All messages must have non-trivial content
        if is_quality:
            for msg in example.messages:
                if len(msg.content.strip()) < 10:  # Arbitrary but reasonable threshold
                    is_quality = False
                    break

        # Last message should be from assistant
        if is_quality and example.messages:
            if example.messages[-1].role != "assistant":
                is_quality = False

        if is_quality:
            kept.append(example)
        else:
            removed.append(example)

    return tuple(kept), tuple(removed)
