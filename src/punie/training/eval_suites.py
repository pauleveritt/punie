"""Pre-defined evaluation suites."""

from punie.training.eval_prompts import EvalPrompt, EvalSuite


def create_baseline_suite() -> EvalSuite:
    """Create the baseline evaluation suite.

    This suite tests fundamental capabilities across tool calling,
    code generation, and reasoning. Used to establish baseline
    performance before training.

    Returns:
        EvalSuite with 5-10 prompts across categories
    """
    prompts = (
        # Tool calling prompts
        EvalPrompt(
            id="tool-01",
            category="tool_calling",
            prompt_text="Read the file at /etc/hosts and tell me what's in it.",
            expected_tool_calls=("read_file",),
            expected_keywords=("localhost", "127.0.0.1"),
        ),
        EvalPrompt(
            id="tool-02",
            category="tool_calling",
            prompt_text="Create a file called test.txt with the content 'Hello World'.",
            expected_tool_calls=("write_file",),
            expected_keywords=("test.txt", "Hello World"),
        ),
        EvalPrompt(
            id="tool-03",
            category="tool_calling",
            prompt_text="Run the command 'echo hello' and show me the output.",
            expected_tool_calls=("run_command",),
            expected_keywords=("hello", "echo"),
        ),
        # Code generation prompts
        EvalPrompt(
            id="code-01",
            category="code_generation",
            prompt_text="Write a Python function that checks if a number is prime.",
            expected_tool_calls=(),
            expected_keywords=("def", "prime", "return"),
        ),
        EvalPrompt(
            id="code-02",
            category="code_generation",
            prompt_text="Write a Python function to calculate factorial recursively.",
            expected_tool_calls=(),
            expected_keywords=("def", "factorial", "return", "recursive"),
        ),
        # Reasoning prompts
        EvalPrompt(
            id="reason-01",
            category="reasoning",
            prompt_text="Explain the difference between a list and a tuple in Python.",
            expected_tool_calls=(),
            expected_keywords=("list", "tuple", "mutable", "immutable"),
        ),
        EvalPrompt(
            id="reason-02",
            category="reasoning",
            prompt_text="What is the time complexity of binary search and why?",
            expected_tool_calls=(),
            expected_keywords=("O(log n)", "binary search", "complexity"),
        ),
    )

    return EvalSuite(name="baseline", prompts=prompts)
