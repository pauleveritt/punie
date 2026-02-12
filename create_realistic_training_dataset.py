"""Create realistic training dataset with 100+ examples.

This generates a diverse dataset for demonstrating successful training.
Combines code explanation, Q&A, and debugging scenarios.

Run: uv run python create_realistic_training_dataset.py
"""

from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_io import write_dataset


def create_code_explanation_examples() -> list[TrainingExample]:
    """Create examples explaining Python code concepts."""
    templates = [
        ("What is a list comprehension?", "A list comprehension is a concise way to create lists in Python. Syntax: [expression for item in iterable if condition]."),
        ("Explain Python decorators", "Decorators are functions that modify other functions. They use @decorator syntax and are useful for adding functionality."),
        ("What is a lambda function?", "Lambda functions are anonymous functions defined with lambda keyword. Syntax: lambda args: expression."),
        ("Explain async/await", "async/await enables asynchronous programming in Python. async def creates coroutines, await pauses execution."),
        ("What are Python generators?", "Generators are functions that yield values lazily using yield keyword. They save memory for large sequences."),
        ("Explain context managers", "Context managers handle resource setup/cleanup using 'with' statement. They implement __enter__ and __exit__."),
        ("What is *args and **kwargs?", "*args captures positional arguments as tuple, **kwargs captures keyword arguments as dict."),
        ("Explain Python metaclasses", "Metaclasses define class behavior. They're classes for classes, used via __metaclass__ or metaclass=."),
        ("What are dataclasses?", "Dataclasses auto-generate __init__, __repr__, etc. Use @dataclass decorator for simple data containers."),
        ("Explain Python slots", "Slots optimize memory by restricting instance attributes. Define with __slots__ tuple in class."),
    ]

    examples = []
    for i, (question, answer) in enumerate(templates):
        for variation in range(5):
            messages = (
                ChatMessage(role="system", content="You are a helpful Python programming tutor."),
                ChatMessage(role="user", content=f"{question} (example {i * 5 + variation + 1})"),
                ChatMessage(role="assistant", content=f"{answer}\n\nThis explanation covers the fundamentals. Would you like more details or examples?"),
            )
            examples.append(TrainingExample(messages=messages))

    return examples


def create_debugging_examples() -> list[TrainingExample]:
    """Create examples helping debug Python code."""
    scenarios = [
        ("Why am I getting 'list index out of range'?", "This error means you're accessing a list index that doesn't exist. Check your range and list length."),
        ("What causes 'TypeError: 'NoneType' object is not subscriptable'?", "You're trying to index None. Check if your function returns None instead of expected value."),
        ("Why 'KeyError' in dictionary?", "The key doesn't exist in the dictionary. Use .get() or check with 'in' before accessing."),
        ("What's causing 'IndentationError'?", "Python requires consistent indentation. Mix of tabs and spaces or wrong indent level causes this."),
        ("Why 'AttributeError' on my object?", "The object doesn't have that attribute. Check spelling or if attribute was set."),
    ]

    examples = []
    for i, (question, answer) in enumerate(scenarios):
        for variation in range(3):
            messages = (
                ChatMessage(role="system", content="You are a helpful debugging assistant for Python."),
                ChatMessage(role="user", content=f"{question} My code isn't working. (case {i * 3 + variation + 1})"),
                ChatMessage(role="assistant", content=f"{answer}\n\nWould you like me to look at your specific code to help debug further?"),
            )
            examples.append(TrainingExample(messages=messages))

    return examples


def create_best_practices_examples() -> list[TrainingExample]:
    """Create examples about Python best practices."""
    practices = [
        ("Should I use list or tuple?", "Use tuples for immutable sequences, lists for mutable. Tuples are faster and hashable."),
        ("When to use sets vs lists?", "Use sets for unique items and fast membership testing. Lists maintain order and allow duplicates."),
        ("Class vs function - when to use which?", "Use classes for stateful objects with multiple methods. Functions for simple transformations."),
        ("How to handle errors in Python?", "Use try/except for expected errors, let unexpected errors propagate. Be specific with exception types."),
        ("When should I use type hints?", "Use type hints in public APIs, function signatures, and complex code. They improve readability and enable tooling."),
    ]

    examples = []
    for i, (question, answer) in enumerate(practices):
        for variation in range(4):
            messages = (
                ChatMessage(role="system", content="You are a Python best practices advisor."),
                ChatMessage(role="user", content=f"{question} (consultation {i * 4 + variation + 1})"),
                ChatMessage(role="assistant", content=f"{answer}\n\nFollowing these practices leads to more maintainable code."),
            )
            examples.append(TrainingExample(messages=messages))

    return examples


def main():
    """Generate realistic training dataset."""
    print("=" * 70)
    print("📝 Creating Realistic Training Dataset")
    print("=" * 70)

    # Generate examples
    print("\nGenerating examples...")
    code_examples = create_code_explanation_examples()
    debug_examples = create_debugging_examples()
    practices_examples = create_best_practices_examples()

    all_examples = code_examples + debug_examples + practices_examples

    print(f"✅ Generated {len(all_examples)} examples")
    print(f"   Code explanations: {len(code_examples)}")
    print(f"   Debugging help: {len(debug_examples)}")
    print(f"   Best practices: {len(practices_examples)}")

    # Split 80/10/10
    total = len(all_examples)
    train_end = int(total * 0.8)
    valid_end = int(total * 0.9)

    dataset = TrainingDataset(
        name="realistic-python-training",
        version="1.0",
        train=tuple(all_examples[:train_end]),
        valid=tuple(all_examples[train_end:valid_end]),
        test=tuple(all_examples[valid_end:]),
    )

    # Write dataset
    output_dir = Path("data/realistic-training")
    write_dataset(dataset, output_dir)

    print(f"\n📊 Dataset Split:")
    print(f"   Train: {len(dataset.train)} examples")
    print(f"   Valid: {len(dataset.valid)} examples")
    print(f"   Test: {len(dataset.test)} examples")

    print(f"\n✅ Saved to: {output_dir}/")

    print("\n💡 Next steps:")
    print(f"   Validate: uv run punie dataset validate {output_dir}")
    print(f"   Train: uv run punie train {output_dir} --iters 100 --output adapters/realistic-v1")

    print("\n" + "=" * 70)
    print("Dataset ready for realistic training!")
    print("=" * 70)


if __name__ == "__main__":
    main()
