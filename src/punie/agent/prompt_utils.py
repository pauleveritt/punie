"""Shared prompt formatting utilities for consistent train/test formatting.

CRITICAL: Always use format_prompt() for prompt formatting. Never use manual
string formatting like f"User: {query}\\nAssistant:" as this causes train/test
format mismatches that can result in catastrophic accuracy loss (60+ points).

Phase 26.1 lesson learned: The model was trained using mlx_lm's automatic
chat template application via tokenizer.apply_chat_template(). Test scripts
that manually formatted prompts caused the model to receive out-of-distribution
input, leading to JavaScript generation, hallucinations, and empty responses.

This module provides a single source of truth that guarantees consistency
with the training pipeline.
"""

from pathlib import Path
from typing import Any, Optional

from transformers import AutoTokenizer


# Global tokenizer cache to avoid reloading on every call
# Note: AutoTokenizer returns various tokenizer types, so we use Any for the value type
_tokenizer_cache: dict[str, Any] = {}


def get_tokenizer(model_path: str | Path) -> Any:
    """Get tokenizer from cache or load from model directory.

    Args:
        model_path: Path to model directory containing tokenizer files

    Returns:
        Loaded tokenizer instance (cached for performance)
        Note: Returns various tokenizer types depending on model

    Example:
        >>> tokenizer = get_tokenizer("fused_model_qwen3_phase27_augmented_5bit")
        >>> tokenizer.name_or_path
        'fused_model_qwen3_phase27_augmented_5bit'
    """
    path_str = str(model_path)

    if path_str not in _tokenizer_cache:
        _tokenizer_cache[path_str] = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True,
        )

    return _tokenizer_cache[path_str]


def clear_tokenizer_cache() -> None:
    """Clear the tokenizer cache.

    Useful for testing or when switching between many models.
    """
    _tokenizer_cache.clear()


def format_prompt(
    query: str,
    model_path: str | Path,
    system_message: Optional[str] = None,
) -> str:
    """Format prompt using model's chat template.

    This is the ONLY way to format prompts for model inference or validation.
    Do NOT use manual string formatting like f"User: {query}\\nAssistant:" as
    this will cause train/test format mismatches.

    This function guarantees consistency with mlx_lm's training pipeline by
    using the same tokenizer.apply_chat_template() API that mlx_lm uses
    internally during training and inference.

    Args:
        query: User query to format
        model_path: Path to model directory (for loading tokenizer)
        system_message: Optional system message (defaults to Punie assistant)

    Returns:
        Formatted prompt string in model's chat template format

    Example:
        >>> # CORRECT: Always use this utility
        >>> prompt = format_prompt("Check types in src/", "fused_model_qwen3_phase27_augmented_5bit")
        >>> prompt.startswith("<|im_start|>system")
        True

        >>> # WRONG: Never do this!
        >>> # prompt = f"User: {query}\\nAssistant:"  # Will cause 60+ point accuracy drop!

    Phase 26.1 lesson learned:
        Using manual formatting caused Phase 26 validation to show 28% accuracy.
        After fixing to use this utility: 88% accuracy (+60 points!).
    """
    if system_message is None:
        system_message = (
            "You are Punie, an AI coding assistant that helps with "
            "Python development via PyCharm."
        )

    tokenizer = get_tokenizer(model_path)

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": query},
    ]

    # This is the EXACT same API that mlx_lm uses internally
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,  # Return string, not token IDs
        add_generation_prompt=True,  # Adds <|im_start|>assistant\n
    )

    return prompt


def format_prompt_with_history(
    query: str,
    model_path: str | Path,
    history: list[dict[str, str]],
    system_message: Optional[str] = None,
) -> str:
    """Format prompt with conversation history.

    Args:
        query: Current user query
        model_path: Path to model directory
        history: List of previous messages [{"role": "user"|"assistant", "content": "..."}]
        system_message: Optional system message

    Returns:
        Formatted prompt with full conversation history

    Example:
        >>> history = [
        ...     {"role": "user", "content": "What is DI?"},
        ...     {"role": "assistant", "content": "Dependency injection is..."},
        ... ]
        >>> prompt = format_prompt_with_history(
        ...     "Show me an example",
        ...     "fused_model_qwen3_phase27_augmented_5bit",
        ...     history=history,
        ... )
    """
    if system_message is None:
        system_message = (
            "You are Punie, an AI coding assistant that helps with "
            "Python development via PyCharm."
        )

    tokenizer = get_tokenizer(model_path)

    # Build full message list: system + history + new query
    messages = [{"role": "system", "content": system_message}]
    messages.extend(history)
    messages.append({"role": "user", "content": query})

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    return prompt


def is_tool_response(response: str) -> bool:
    """Check if response contains a tool call.

    This is the unified implementation used across all validation and benchmarking
    scripts to ensure consistent tool detection logic.

    Args:
        response: Model response text

    Returns:
        True if response contains a tool call, False otherwise

    Detects:
        - XML format: <tool_call>
        - Code Mode: ```python with execute_code
        - JSON format: ```json

    Example:
        >>> is_tool_response("<tool_call>result = typecheck('src/')</tool_call>")
        True
        >>> is_tool_response("Dependency injection is a design pattern...")
        False
    """
    return (
        "<tool_call>" in response
        or ("```python" in response and "execute_code" in response)
        or "```json" in response
    )


def validate_python_code(code: str) -> tuple[bool, str | None]:
    """Validate Python code using AST parsing.

    Args:
        code: Python code string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if code is syntactically valid
        - error_message: Error description if invalid, None otherwise

    Example:
        >>> validate_python_code("x = 1 + 2")
        (True, None)
        >>> is_valid, error = validate_python_code("x = 1 +")
        >>> is_valid
        False
        >>> error.startswith("SyntaxError:")
        True
    """
    import ast

    try:
        ast.parse(code)
        return (True, None)
    except SyntaxError as e:
        return (False, f"SyntaxError: {e}")
    except Exception as e:
        return (False, f"Parse error: {e}")


def extract_tool_calls_from_response(response: str) -> list[str]:
    """Extract tool call code blocks from model response.

    Args:
        response: Model response text

    Returns:
        List of Python code strings (from <tool_call> blocks or ```python blocks)

    Example:
        >>> response = "<tool_call>result = typecheck('src/')</tool_call>"
        >>> extract_tool_calls_from_response(response)
        ["result = typecheck('src/')"]
    """
    import re

    code_blocks = []

    # Extract from <tool_call>...</tool_call>
    tool_call_pattern = r"<tool_call>(.*?)</tool_call>"
    for match in re.finditer(tool_call_pattern, response, re.DOTALL):
        code_blocks.append(match.group(1).strip())

    # Extract from ```python ... ``` (Code Mode)
    python_block_pattern = r"```python\n(.*?)```"
    for match in re.finditer(python_block_pattern, response, re.DOTALL):
        code = match.group(1).strip()
        if "execute_code" in code:
            code_blocks.append(code)

    return code_blocks


def extract_python_from_code_mode(raw_block: str) -> str | None:
    """Extract Python code from Code Mode XML wrapper.

    Args:
        raw_block: Raw tool call block (may contain <parameter=code> wrapper)

    Returns:
        Pure Python code string, or None if extraction fails

    Example:
        >>> raw = '<function=execute_code><parameter=code>result = typecheck("src/")</parameter></function>'
        >>> extract_python_from_code_mode(raw)
        'result = typecheck("src/")'

        >>> raw = 'result = typecheck("src/")'  # Already clean
        >>> extract_python_from_code_mode(raw)
        'result = typecheck("src/")'
    """
    import re

    # Try to extract from <parameter=code>...</parameter> wrapper
    match = re.search(r'<parameter=code>\s*(.*?)\s*</parameter>', raw_block, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no wrapper found, check if it's already clean Python
    cleaned = raw_block.strip()
    if cleaned and not cleaned.startswith('<'):
        return cleaned

    return None


# Export public API
__all__ = [
    "format_prompt",
    "format_prompt_with_history",
    "get_tokenizer",
    "clear_tokenizer_cache",
    "is_tool_response",
    "validate_python_code",
    "extract_tool_calls_from_response",
    "extract_python_from_code_mode",
]
