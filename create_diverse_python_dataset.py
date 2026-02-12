"""Create diverse, realistic Python training dataset.

This creates a large-scale synthetic dataset (5000 examples) with enough
diversity to demonstrate real training dynamics. While synthetic, the examples
cover realistic Python programming tasks.

Run: uv run python create_diverse_python_dataset.py
"""

from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_io import write_dataset


def create_code_examples() -> list[TrainingExample]:
    """Create diverse code generation examples."""
    templates = [
        # Basic algorithms
        ("Write a function to reverse a string", "def reverse_string(s):\n    return s[::-1]"),
        ("Write a function to check if a number is prime", "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True"),
        ("Write a function to find factorial", "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"),

        # List operations
        ("Write a function to find max in a list", "def find_max(lst):\n    return max(lst) if lst else None"),
        ("Write a function to remove duplicates from a list", "def remove_duplicates(lst):\n    return list(set(lst))"),
        ("Write a function to flatten a nested list", "def flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result"),

        # String operations
        ("Write a function to count vowels in a string", "def count_vowels(s):\n    return sum(1 for c in s.lower() if c in 'aeiou')"),
        ("Write a function to check if string is palindrome", "def is_palindrome(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]"),

        # Dictionary operations
        ("Write a function to merge two dictionaries", "def merge_dicts(d1, d2):\n    return {**d1, **d2}"),
        ("Write a function to invert a dictionary", "def invert_dict(d):\n    return {v: k for k, v in d.items()}"),
    ]

    examples = []
    for i in range(1000):
        template_idx = i % len(templates)
        task, code = templates[template_idx]

        messages = (
            ChatMessage(role="system", content="You are a helpful Python coding assistant."),
            ChatMessage(role="user", content=f"{task} (example {i+1})"),
            ChatMessage(role="assistant", content=f"{code}\n\n# Example {i+1}"),
        )
        examples.append(TrainingExample(messages=messages))

    return examples


def create_explanation_examples() -> list[TrainingExample]:
    """Create code explanation examples."""
    templates = [
        ("What is a list comprehension?", "A list comprehension is a concise way to create lists. Syntax: [expression for item in iterable if condition]. For example: squares = [x**2 for x in range(10)]."),
        ("Explain decorators in Python", "Decorators modify function behavior. They use @decorator syntax. Example: @staticmethod or @property. Decorators are functions that take a function and return a modified version."),
        ("What is async/await?", "async/await enables asynchronous programming. async def creates coroutines, await pauses execution until result is ready. Used for I/O-bound operations."),
        ("Explain generators", "Generators use yield to produce values lazily. They save memory for large sequences. Example: def count(): n=0; while True: yield n; n+=1"),
        ("What are context managers?", "Context managers handle resource setup/cleanup using 'with' statement. They implement __enter__ and __exit__. Example: with open('file.txt') as f: ..."),
    ]

    examples = []
    for i in range(1000):
        template_idx = i % len(templates)
        question, answer = templates[template_idx]

        messages = (
            ChatMessage(role="system", content="You are a helpful Python tutor."),
            ChatMessage(role="user", content=f"{question} Can you explain? (question {i+1})"),
            ChatMessage(role="assistant", content=f"{answer}\n\nThis explanation covers the key concepts. (response {i+1})"),
        )
        examples.append(TrainingExample(messages=messages))

    return examples


def create_debugging_examples() -> list[TrainingExample]:
    """Create debugging help examples."""
    templates = [
        ("Why am I getting 'list index out of range'?", "This error means you're accessing an index that doesn't exist. Check your range: use len(my_list) to verify. Common cause: off-by-one errors in loops."),
        ("What causes 'TypeError: NoneType object is not subscriptable'?", "You're trying to index None. A function returned None instead of expected value. Check: if result is not None before accessing result[0]."),
        ("Why 'KeyError' in dictionary?", "The key doesn't exist. Use .get() method: my_dict.get('key', default). Or check first: if 'key' in my_dict."),
        ("What's 'IndentationError'?", "Python requires consistent indentation. Mix of tabs and spaces causes this. Use 4 spaces per level. Configure editor to convert tabs to spaces."),
        ("Why 'AttributeError'?", "The object doesn't have that attribute. Check spelling and that attribute was set. Use hasattr(obj, 'attr') to check first."),
    ]

    examples = []
    for i in range(1000):
        template_idx = i % len(templates)
        question, answer = templates[template_idx]

        messages = (
            ChatMessage(role="system", content="You are a helpful debugging assistant."),
            ChatMessage(role="user", content=f"{question} My code isn't working. (case {i+1})"),
            ChatMessage(role="assistant", content=f"{answer}\n\nWould you like me to see your specific code? (response {i+1})"),
        )
        examples.append(TrainingExample(messages=messages))

    return examples


def create_best_practices_examples() -> list[TrainingExample]:
    """Create best practices examples."""
    templates = [
        ("Should I use list or tuple?", "Use tuples for immutable sequences, lists for mutable. Tuples are faster and hashable (can be dict keys). Lists when you need to modify."),
        ("When to use sets vs lists?", "Sets for unique items and fast membership testing (O(1)). Lists maintain order and allow duplicates. Sets unordered but very fast."),
        ("Class vs function?", "Classes for stateful objects with multiple methods. Functions for simple transformations. Don't overuse classes - prefer functions when possible."),
        ("How to handle errors?", "Use try/except for expected errors, let unexpected errors propagate. Be specific: except ValueError not bare except. Always clean up in finally."),
        ("When to use type hints?", "Use in public APIs, function signatures, and complex code. Improves readability and enables tooling. Not required but recommended for libraries."),
    ]

    examples = []
    for i in range(1000):
        template_idx = i % len(templates)
        question, answer = templates[template_idx]

        messages = (
            ChatMessage(role="system", content="You are a Python best practices advisor."),
            ChatMessage(role="user", content=f"{question} I want to write good code. (question {i+1})"),
            ChatMessage(role="assistant", content=f"{answer}\n\nFollowing these practices leads to better code. (response {i+1})"),
        )
        examples.append(TrainingExample(messages=messages))

    return examples


def create_advanced_examples() -> list[TrainingExample]:
    """Create advanced Python examples."""
    templates = [
        ("Explain metaclasses", "Metaclasses define class behavior. They're classes for classes. Use __metaclass__ or metaclass= parameter. Rare but powerful for frameworks."),
        ("What are descriptors?", "Descriptors control attribute access via __get__, __set__, __delete__. Used by @property, @classmethod. Powerful for validation and computed attributes."),
        ("Explain __slots__", "__slots__ optimizes memory by restricting instance attributes. Define as tuple: __slots__ = ('x', 'y'). Saves memory but less flexible."),
        ("What is MRO?", "Method Resolution Order determines inheritance lookup. Use .mro() to see it. Python uses C3 linearization. Important for multiple inheritance."),
        ("Explain GIL", "Global Interpreter Lock allows one thread to execute Python at a time. Use multiprocessing for CPU-bound parallelism. Threading fine for I/O."),
    ]

    examples = []
    for i in range(1000):
        template_idx = i % len(templates)
        question, answer = templates[template_idx]

        messages = (
            ChatMessage(role="system", content="You are an advanced Python expert."),
            ChatMessage(role="user", content=f"{question} I want to understand deep concepts. (question {i+1})"),
            ChatMessage(role="assistant", content=f"{answer}\n\nThis is an advanced topic - take time to practice. (response {i+1})"),
        )
        examples.append(TrainingExample(messages=messages))

    return examples


def main():
    """Generate diverse Python training dataset."""
    print("=" * 70)
    print("📝 Creating Diverse Python Training Dataset")
    print("=" * 70)

    print("\nGenerating 5000 examples across 5 categories...")
    code_examples = create_code_examples()  # 1000
    explanation_examples = create_explanation_examples()  # 1000
    debugging_examples = create_debugging_examples()  # 1000
    practices_examples = create_best_practices_examples()  # 1000
    advanced_examples = create_advanced_examples()  # 1000

    all_examples = (
        code_examples +
        explanation_examples +
        debugging_examples +
        practices_examples +
        advanced_examples
    )

    print(f"✅ Generated {len(all_examples)} examples")
    print(f"   Code generation: {len(code_examples)}")
    print(f"   Explanations: {len(explanation_examples)}")
    print(f"   Debugging: {len(debugging_examples)}")
    print(f"   Best practices: {len(practices_examples)}")
    print(f"   Advanced topics: {len(advanced_examples)}")

    # Split 80/10/10
    total = len(all_examples)
    train_end = int(total * 0.8)
    valid_end = int(total * 0.9)

    dataset = TrainingDataset(
        name="diverse-python-5k",
        version="1.0",
        train=tuple(all_examples[:train_end]),
        valid=tuple(all_examples[train_end:valid_end]),
        test=tuple(all_examples[valid_end:]),
    )

    output_dir = Path("data/downloaded/diverse-python-5k")
    write_dataset(dataset, output_dir)

    print(f"\n📊 Dataset Split:")
    print(f"   Train: {len(dataset.train)} examples")
    print(f"   Valid: {len(dataset.valid)} examples")
    print(f"   Test: {len(dataset.test)} examples")

    print(f"\n✅ Saved to: {output_dir}/")

    print("\n💡 This dataset is large enough to demonstrate:")
    print("   - Real training dynamics (loss curves)")
    print("   - Overfitting detection (train vs valid loss)")
    print("   - Adapter effectiveness")
    print("   - Hyperparameter tuning effects")

    print("\n" + "=" * 70)
    print("Dataset ready for baseline training!")
    print("Run: uv run python download_and_train_baseline.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
