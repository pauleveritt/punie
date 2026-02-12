"""Dataset download utilities using HuggingFace datasets library.

All downloaders stream datasets (never download full corpus) and convert
to TrainingExample format compatible with mlx_lm.lora.
"""

from pathlib import Path

from punie.training.dataset import ChatMessage, DatasetStats, TrainingExample
from punie.training.dataset_io import write_jsonl


def _convert_to_chat_format(text: str, is_code: bool = False) -> tuple[ChatMessage, ...]:
    """Convert plain text to chat completion format.

    Args:
        text: Text content
        is_code: Whether content is code (affects system message)

    Returns:
        Tuple of ChatMessage objects
    """
    if is_code:
        system_msg = "You are a helpful coding assistant."
        user_msg = "Write code to accomplish the following task:"
    else:
        system_msg = "You are a helpful assistant."
        user_msg = "Please explain the following:"

    return (
        ChatMessage(role="system", content=system_msg),
        ChatMessage(role="user", content=user_msg),
        ChatMessage(role="assistant", content=text),
    )


def download_sample_dataset(
    output_dir: Path,
    max_examples: int = 100,
) -> DatasetStats:
    """Generate a small synthetic sample dataset for testing.

    Creates simple synthetic examples for testing the training infrastructure.
    This is for testing - not real training data.

    Args:
        output_dir: Output directory for JSONL files
        max_examples: Number of examples to generate (default: 100)

    Returns:
        DatasetStats with generation summary
    """
    # Generate synthetic examples
    examples = []

    templates = [
        ("Explain what a Python function is", "A Python function is defined with the def keyword..."),
        ("How do I create a list in Python?", "You can create a list in Python using square brackets: my_list = [1, 2, 3]"),
        ("What is a for loop?", "A for loop in Python iterates over a sequence using: for item in sequence:"),
        ("Explain variables in Python", "Variables in Python store data and are created by assignment: x = 10"),
        ("What are strings in Python?", "Strings are text data enclosed in quotes: my_string = 'hello'"),
    ]

    for i in range(max_examples):
        template_idx = i % len(templates)
        question, answer = templates[template_idx]

        # Add variation
        question_var = f"{question} (Example {i+1})"
        answer_var = f"{answer}\n\nThis is example number {i+1}."

        messages = (
            ChatMessage(role="system", content="You are a helpful Python tutor."),
            ChatMessage(role="user", content=question_var),
            ChatMessage(role="assistant", content=answer_var),
        )
        examples.append(TrainingExample(messages=messages))

    # Split into train/valid/test (80/10/10)
    n = len(examples)
    train_end = int(n * 0.8)
    valid_end = int(n * 0.9)

    train_examples = tuple(examples[:train_end])
    valid_examples = tuple(examples[train_end:valid_end])
    test_examples = tuple(examples[valid_end:])

    # Write to JSONL files
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(train_examples, output_dir / "train.jsonl")
    write_jsonl(valid_examples, output_dir / "valid.jsonl")
    write_jsonl(test_examples, output_dir / "test.jsonl")

    # Compute statistics
    total = len(train_examples) + len(valid_examples) + len(test_examples)
    avg_messages = sum(len(ex.messages) for ex in examples) / max(len(examples), 1)

    return DatasetStats(
        total_examples=total,
        train_count=len(train_examples),
        valid_count=len(valid_examples),
        test_count=len(test_examples),
        avg_messages_per_example=avg_messages,
    )


def download_python_code_dataset(
    output_dir: Path,
    max_examples: int = 1000,
) -> DatasetStats:
    """Download Python code examples for training.

    Uses bigcode/the-stack-dedup dataset (Apache 2.0 License).
    This is a large, actively-maintained dataset of source code.

    Args:
        output_dir: Output directory for JSONL files
        max_examples: Maximum examples to download (default: 1000)

    Returns:
        DatasetStats with download summary
    """
    from datasets import load_dataset

    # Load Python subset of The Stack (deduplicated)
    # This dataset is Apache 2.0 licensed and actively maintained
    dataset = load_dataset(
        "bigcode/the-stack-dedup",
        data_dir="data/python",
        split="train",
        streaming=True,
    )

    examples = []
    for i, item in enumerate(dataset):
        if i >= max_examples:
            break

        # Extract code content
        code = item.get("content", "")

        # Skip if too short or likely not useful
        if len(code.strip()) < 100:
            continue

        # Skip files that are mostly comments or imports
        code_lines = [line for line in code.split("\n") if line.strip() and not line.strip().startswith("#")]
        if len(code_lines) < 5:
            continue

        # Create chat format: code explanation task
        messages = (
            ChatMessage(role="system", content="You are a helpful Python coding assistant."),
            ChatMessage(role="user", content="Write Python code to solve a programming task:"),
            ChatMessage(role="assistant", content=code),
        )

        examples.append(TrainingExample(messages=messages))

    # Split into train/valid/test (80/10/10)
    n = len(examples)
    train_end = int(n * 0.8)
    valid_end = int(n * 0.9)

    train_examples = tuple(examples[:train_end])
    valid_examples = tuple(examples[train_end:valid_end])
    test_examples = tuple(examples[valid_end:])

    # Write to JSONL files
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(train_examples, output_dir / "train.jsonl")
    write_jsonl(valid_examples, output_dir / "valid.jsonl")
    write_jsonl(test_examples, output_dir / "test.jsonl")

    # Compute statistics
    total = len(train_examples) + len(valid_examples) + len(test_examples)
    avg_messages = sum(len(ex.messages) for ex in examples) / max(len(examples), 1)

    return DatasetStats(
        total_examples=total,
        train_count=len(train_examples),
        valid_count=len(valid_examples),
        test_count=len(test_examples),
        avg_messages_per_example=avg_messages,
    )
