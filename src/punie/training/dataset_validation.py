"""Dataset validation functions."""

from punie.training.dataset import TrainingDataset, TrainingExample


def validate_example(example: TrainingExample) -> list[str]:
    """Validate a single training example.

    Checks for common issues that would cause training to fail.

    Args:
        example: Training example to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Must have at least 2 messages (user + assistant minimum)
    if len(example.messages) < 2:
        errors.append(f"Example has {len(example.messages)} messages, need at least 2")

    # Last message should be from assistant (what we're training to predict)
    if example.messages and example.messages[-1].role != "assistant":
        errors.append(
            f"Last message role is '{example.messages[-1].role}', should be 'assistant'"
        )

    # All roles must be valid
    valid_roles = {"system", "user", "assistant"}
    for i, msg in enumerate(example.messages):
        if msg.role not in valid_roles:
            errors.append(
                f"Message {i} has invalid role '{msg.role}', "
                f"must be one of {valid_roles}"
            )

    # Messages should have non-empty content
    for i, msg in enumerate(example.messages):
        if not msg.content or not msg.content.strip():
            errors.append(f"Message {i} has empty content")

    return errors


def validate_dataset(dataset: TrainingDataset) -> list[str]:
    """Validate a complete training dataset.

    Checks both structure and individual examples.

    Args:
        dataset: Dataset to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # At least one split should be non-empty
    if not dataset.train and not dataset.valid and not dataset.test:
        errors.append("Dataset has no examples in any split")

    # Training split should not be empty
    if not dataset.train:
        errors.append("Training split is empty (at least some examples needed)")

    # Validate each example in each split
    for split_name, split_examples in [
        ("train", dataset.train),
        ("valid", dataset.valid),
        ("test", dataset.test),
    ]:
        for i, example in enumerate(split_examples):
            example_errors = validate_example(example)
            for error in example_errors:
                errors.append(f"{split_name}[{i}]: {error}")

    return errors
