"""Training dataset dataclasses and utilities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    """A single message in a chat conversation.

    Follows the standard chat completion format used by OpenAI, Anthropic, etc.
    """

    role: str  # "system", "user", or "assistant"
    content: str  # Message text


@dataclass(frozen=True)
class TrainingExample:
    """A single training example in chat completion format.

    Represents one complete conversation that can be used for fine-tuning.
    """

    messages: tuple[ChatMessage, ...]  # Conversation messages

    def to_jsonl_dict(self) -> dict:
        """Convert to JSONL-compatible dictionary.

        Returns format compatible with mlx_lm.lora training:
        {"messages": [{"role": "...", "content": "..."}, ...]}
        """
        return {
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in self.messages
            ]
        }


@dataclass(frozen=True)
class TrainingDataset:
    """A complete training dataset with train/validation/test splits.

    All splits are immutable tuples for reproducibility.
    """

    name: str  # Dataset identifier (e.g., "baseline-v1", "step-a")
    version: str  # Version string (e.g., "2026-02-11")
    train: tuple[TrainingExample, ...]  # Training examples
    valid: tuple[TrainingExample, ...]  # Validation examples
    test: tuple[TrainingExample, ...]  # Test examples


@dataclass(frozen=True)
class DatasetStats:
    """Statistics about a training dataset.

    Useful for understanding dataset composition and quality.
    """

    total_examples: int  # Total across all splits
    train_count: int
    valid_count: int
    test_count: int
    avg_messages_per_example: float  # Average conversation length
    categories: dict[str, int] | None = None  # Optional category breakdown
