"""Evaluation results and reporting."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvalResult:
    """Result from evaluating a single prompt.

    Captures the model's response, tool calls made, duration, and computed score.
    """

    prompt_id: str  # ID of the evaluated prompt
    response_text: str  # Model's response
    tool_calls_made: tuple[str, ...]  # Names of tools that were called
    duration_ms: float  # Time taken to generate response
    score: float  # Computed score (0.0 to 1.0)
    success: bool  # Whether evaluation succeeded (False if error/timeout)


@dataclass(frozen=True)
class EvalReport:
    """Complete evaluation report for a model/adapter combination.

    Contains all results and metadata for a full evaluation run.
    """

    model_name: str  # Model identifier
    adapter_path: str | None  # LoRA adapter path (None = base model)
    suite_name: str  # Name of the evaluation suite
    timestamp: datetime  # When evaluation was run
    results: tuple[EvalResult, ...]  # All evaluation results

    @property
    def overall_score(self) -> float:
        """Calculate overall score across all results.

        Returns:
            Average score (0.0 to 1.0), or 0.0 if no results
        """
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def success_rate(self) -> float:
        """Calculate success rate (fraction of prompts that succeeded).

        Returns:
            Success rate (0.0 to 1.0), or 0.0 if no results
        """
        if not self.results:
            return 0.0
        successful = sum(1 for r in self.results if r.success)
        return successful / len(self.results)

    def score_by_category(self, category_results: dict[str, list[EvalResult]]) -> dict[str, float]:
        """Calculate average score for each category.

        Args:
            category_results: Mapping from category name to list of results

        Returns:
            Mapping from category name to average score
        """
        scores = {}
        for category, results_list in category_results.items():
            if results_list:
                scores[category] = sum(r.score for r in results_list) / len(results_list)
            else:
                scores[category] = 0.0
        return scores
