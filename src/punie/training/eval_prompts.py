"""Evaluation prompt definitions and suites."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalPrompt:
    """A single evaluation prompt with expected outputs.

    Used to test model capabilities across different categories.
    """

    id: str  # Unique identifier (e.g., "tool-01", "code-01")
    category: str  # Category: "tool_calling", "code_generation", "reasoning"
    prompt_text: str  # The actual prompt to send to the model
    expected_tool_calls: tuple[str, ...] = ()  # Tool names we expect to be called
    expected_keywords: tuple[str, ...] = ()  # Keywords we expect in the response


@dataclass(frozen=True)
class EvalSuite:
    """A collection of evaluation prompts.

    Organizes prompts into a named suite for batch evaluation.
    """

    name: str  # Suite name (e.g., "baseline", "tool-calling-v1")
    prompts: tuple[EvalPrompt, ...]  # All prompts in this suite

    def by_category(self, category: str) -> tuple[EvalPrompt, ...]:
        """Filter prompts by category.

        Args:
            category: Category to filter by (e.g., "tool_calling")

        Returns:
            Tuple of prompts matching the category
        """
        return tuple(p for p in self.prompts if p.category == category)
