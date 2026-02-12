"""Evaluation suite for autonomous tool usage capability.

This suite tests whether models autonomously decide to use tools WITHOUT
explicit instructions. Traditional evals test tool execution; this tests
tool decision-making.
"""

from dataclasses import dataclass

from punie.training.eval_prompts import EvalPrompt, EvalSuite


@dataclass(frozen=True)
class AutonomousToolPrompt:
    """Evaluation prompt that requires autonomous tool usage decision.

    Unlike standard EvalPrompt, these prompts DO NOT explicitly instruct
    the model to use tools. The model must figure out it needs to search/read.
    """

    id: str
    category: str
    prompt_text: str
    expected_tool_calls: tuple[str, ...]  # Tools model should autonomously use
    expected_keywords: tuple[str, ...]  # Content expected in final answer
    reasoning_required: str  # Why tools are needed for this task


def create_autonomous_tool_suite() -> EvalSuite:
    """Create evaluation suite for autonomous tool usage.

    Tests whether models know WHEN to use tools, not just HOW to use them.
    All prompts require codebase search/analysis but don't explicitly say so.

    Returns:
        EvalSuite with autonomous tool usage prompts
    """
    prompts = (
        # Category: Code Search (must decide to grep/search)
        EvalPrompt(
            id="auto-search-protocol",
            category="autonomous_code_search",
            prompt_text="Which classes in this codebase subclass from Protocol?",
            expected_tool_calls=("run_command",),  # Should grep for Protocol
            expected_keywords=("HttpAppFactory", "Client", "Agent"),
        ),
        EvalPrompt(
            id="auto-search-imports",
            category="autonomous_code_search",
            prompt_text="List the files that import 'asyncio'",
            expected_tool_calls=("run_command",),  # Should grep for asyncio imports
            expected_keywords=("import asyncio", ".py"),
        ),
        EvalPrompt(
            id="auto-search-dataclass",
            category="autonomous_code_search",
            prompt_text="Find all dataclasses in the training module",
            expected_tool_calls=("run_command",),  # Should search for @dataclass
            expected_keywords=("@dataclass", "frozen=True"),
        ),
        EvalPrompt(
            id="auto-search-function",
            category="autonomous_code_search",
            prompt_text="What does the create_pydantic_agent function do?",
            expected_tool_calls=("run_command", "read_file"),  # Should find+read file
            expected_keywords=("agent", "model", "toolset"),
        ),
        # Category: Code Analysis (must decide to read files)
        EvalPrompt(
            id="auto-read-config",
            category="autonomous_code_analysis",
            prompt_text="What port does the HTTP server use by default?",
            expected_tool_calls=("run_command", "read_file"),  # Should find+read config
            expected_keywords=("port", "8080"),
        ),
        EvalPrompt(
            id="auto-read-tests",
            category="autonomous_code_analysis",
            prompt_text="How many test files are in this project?",
            expected_tool_calls=("run_command",),  # Should count test files
            expected_keywords=("test_", ".py"),
        ),
        EvalPrompt(
            id="auto-read-dependencies",
            category="autonomous_code_analysis",
            prompt_text="What version of PydanticAI does this project use?",
            expected_tool_calls=("read_file",),  # Should read pyproject.toml
            expected_keywords=("pydantic-ai", "pydantic_ai"),
        ),
        # Category: Multi-Step Reasoning (must chain multiple tools)
        EvalPrompt(
            id="auto-multi-find-and-read",
            category="autonomous_multi_step",
            prompt_text="Show me the docstring for the run_command function",
            expected_tool_calls=("run_command", "read_file"),  # Find file, then read
            expected_keywords=("Run a shell command", "terminal"),
        ),
        EvalPrompt(
            id="auto-multi-count-and-list",
            category="autonomous_multi_step",
            prompt_text="How many Protocol classes are there and what are they?",
            expected_tool_calls=("run_command",),  # Search and count
            expected_keywords=("Protocol", "HttpAppFactory", "6"),
        ),
        EvalPrompt(
            id="auto-multi-compare",
            category="autonomous_multi_step",
            prompt_text="Compare the size of the training module vs the HTTP module",
            expected_tool_calls=("run_command",),  # Must count files or lines
            expected_keywords=("training", "http", "files"),
        ),
        # Category: Negative Tests (should NOT use tools)
        EvalPrompt(
            id="auto-negative-math",
            category="autonomous_no_tools_needed",
            prompt_text="What is 25 multiplied by 4?",
            expected_tool_calls=(),  # Should answer directly, no tools
            expected_keywords=("100",),
        ),
        EvalPrompt(
            id="auto-negative-concept",
            category="autonomous_no_tools_needed",
            prompt_text="What is the purpose of type hints in Python?",
            expected_tool_calls=(),  # General knowledge, no codebase search
            expected_keywords=("type", "static", "check"),
        ),
    )

    return EvalSuite(
        name="autonomous-tool-usage",
        prompts=prompts,
    )


def score_autonomous_tool_usage(
    tool_calls_made: tuple[str, ...],
    expected_tool_calls: tuple[str, ...],
    keywords_found: tuple[str, ...],
    expected_keywords: tuple[str, ...],
) -> dict[str, float]:
    """Score autonomous tool usage performance.

    Separate scores for:
    - Decision-making: Did model use tools when needed?
    - Correctness: Were the right tools used?
    - Accuracy: Did final answer contain expected content?

    Args:
        tool_calls_made: Tools the model actually called
        expected_tool_calls: Tools we expected to be called
        keywords_found: Keywords found in response
        expected_keywords: Keywords we expected in response

    Returns:
        Dict with 'decision', 'correctness', 'accuracy', 'overall' scores
    """
    # Decision score: Did model use ANY tools when it should have?
    if len(expected_tool_calls) == 0:
        # Negative test: should NOT use tools
        decision_score = 1.0 if len(tool_calls_made) == 0 else 0.0
    else:
        # Positive test: SHOULD use tools
        decision_score = 1.0 if len(tool_calls_made) > 0 else 0.0

    # Correctness score: Were the RIGHT tools used?
    if len(expected_tool_calls) == 0:
        correctness_score = 1.0  # N/A for negative tests
    else:
        # Check if expected tools were called
        expected_set = set(expected_tool_calls)
        called_set = set(tool_calls_made)
        correct_calls = len(expected_set & called_set)
        correctness_score = correct_calls / len(expected_set) if expected_set else 1.0

    # Accuracy score: Did final answer contain expected keywords?
    if len(expected_keywords) == 0:
        accuracy_score = 1.0  # No keywords to check
    else:
        found_count = len(keywords_found)
        total_expected = len(expected_keywords)
        accuracy_score = found_count / total_expected if total_expected > 0 else 1.0

    # Overall: Average of all three (all equally important)
    overall_score = (decision_score + correctness_score + accuracy_score) / 3

    return {
        "decision": decision_score,
        "correctness": correctness_score,
        "accuracy": accuracy_score,
        "overall": overall_score,
    }


# Example usage documentation
USAGE_EXAMPLES = """

Example:
--------
```python
from punie.training.eval_autonomous_tool_usage import create_autonomous_tool_suite
from punie.training.eval_runner import run_evaluation, EvalRunConfig
from punie.training.server_config import ServerConfig

# Create suite
suite = create_autonomous_tool_usage()

# Run evaluation
config = EvalRunConfig(
    suite=suite,
    server_config=ServerConfig(
        model_path="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        port=8080,
    ),
    workspace=Path.cwd(),
    manage_server=True,
)

report = await run_evaluation(config)
print(f"Autonomous tool usage score: {report.overall_score:.2%}")
```

Interpretation:
---------------
- **90-100%**: Model autonomously uses tools when needed
- **70-89%**: Model sometimes uses tools, needs prompting
- **50-69%**: Weak autonomous tool usage, often guesses
- **<50%**: Model doesn't autonomously use tools (hallucinate)

This suite is designed to distinguish between:
1. Models that know WHEN to use tools (30B+)
2. Models that CAN use tools but don't know WHEN (1.5B)
3. Models that lack tool usage entirely
"""
