# Prompt Format Consistency: Solutions and Trade-offs

## The Problem

Phase 26.1 revealed a critical bug: training used ChatML format (via mlx_lm's automatic chat template), but test scripts manually formatted prompts as plain text. This caused a 60-point accuracy drop.

**Root cause:** Two different prompt formatting code paths.

## Solution Options

### Option A: Use Tokenizer Chat Template Everywhere (RECOMMENDED)

**Approach:** Always use the tokenizer's `apply_chat_template()` method instead of manual string formatting.

**Why this works:**
- mlx_lm automatically uses `tokenizer.apply_chat_template()` during training and inference
- Using the same API guarantees consistency
- No validation overhead - you can't get it wrong if there's only one code path

**Implementation:**

```python
# src/punie/agent/prompt_formatting.py
from pathlib import Path
from transformers import AutoTokenizer


def load_tokenizer(model_path: str | Path):
    """Load tokenizer from model directory."""
    return AutoTokenizer.from_pretrained(model_path)


def format_prompt_with_tokenizer(
    tokenizer,
    query: str,
    system_message: str = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."
) -> str:
    """Format prompt using tokenizer's chat template.

    This guarantees consistency with training/inference because it uses
    the SAME code path that mlx_lm uses internally.
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": query},
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,  # Adds <|im_start|>assistant\n
    )


# Usage in test scripts:
def run_validation_suite(model_path: str) -> dict:
    model, tokenizer = load(model_path)

    for query in test_queries:
        # CORRECT: Uses tokenizer's chat template
        prompt = format_prompt_with_tokenizer(tokenizer, query)

        response = generate(model, tokenizer, prompt=prompt, max_tokens=500)
```

**Pros:**
- ✅ Zero overhead (same as manual formatting)
- ✅ Guaranteed consistency with mlx_lm
- ✅ Works with any model (chat template is model-specific)
- ✅ Handles special tokens correctly
- ✅ Single source of truth

**Cons:**
- ❌ Requires loading tokenizer (small cost)
- ❌ Still possible to accidentally use manual formatting

**Verdict:** **This is the correct solution.** Use the tokenizer API, don't reinvent it.

---

### Option B: Pydantic Validation (Defense in Depth)

**Approach:** Add runtime validation to catch prompt format mismatches.

**Implementation:**

```python
# src/punie/agent/prompt_validation.py
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Single message in chat format."""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatMLPrompt(BaseModel):
    """Validates that a prompt follows Qwen3 ChatML format.

    Expected format:
        <|im_start|>system
        {system_message}<|im_end|>
        <|im_start|>user
        {user_message}<|im_end|>
        <|im_start|>assistant
    """
    raw_prompt: str

    @field_validator("raw_prompt")
    @classmethod
    def validate_chatml_format(cls, v: str) -> str:
        """Validate prompt follows ChatML format."""
        required_tokens = [
            "<|im_start|>system",
            "<|im_end|>",
            "<|im_start|>user",
            "<|im_start|>assistant",
        ]

        for token in required_tokens:
            if token not in v:
                raise ValueError(
                    f"Prompt missing required ChatML token: {token}\n"
                    f"Got: {v[:100]}..."
                )

        # Check for common wrong formats
        wrong_patterns = [
            "User:",
            "Assistant:",
            "Human:",
            "AI:",
        ]

        for pattern in wrong_patterns:
            if pattern in v and "<|im_start|>" not in v:
                raise ValueError(
                    f"Prompt uses plain text format ('{pattern}') instead of ChatML.\n"
                    f"Use format_prompt_with_tokenizer() instead of manual formatting."
                )

        return v


class PromptFormatter:
    """Prompt formatter with optional validation."""

    def __init__(self, tokenizer, validate: bool = True):
        self.tokenizer = tokenizer
        self.validate = validate

    def format(
        self,
        query: str,
        system_message: str = "You are Punie, an AI coding assistant..."
    ) -> str:
        """Format prompt with optional validation."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": query},
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        # Optional validation
        if self.validate:
            ChatMLPrompt(raw_prompt=prompt)  # Raises ValidationError if wrong

        return prompt


# Usage:
formatter = PromptFormatter(tokenizer, validate=True)
prompt = formatter.format("Check types in src/")  # Validates automatically
```

**Pros:**
- ✅ Catches format mismatches at runtime
- ✅ Self-documenting (shows expected format)
- ✅ Can be disabled in production (validate=False)
- ✅ Prevents "User:" / "Assistant:" mistakes

**Cons:**
- ❌ Performance overhead (~0.1-0.5ms per prompt)
- ❌ Redundant if using tokenizer API correctly
- ❌ Can't catch all format issues (e.g., wrong chat template file)
- ❌ Adds complexity

**When to use:** Only if you want defense-in-depth during development/testing. Disable in production.

---

### Option C: Training Data Format Validator (Pre-training Check)

**Approach:** Validate training data format matches tokenizer's chat template BEFORE training starts.

**Implementation:**

```python
# src/punie/training/format_validator.py
from pathlib import Path
from transformers import AutoTokenizer
from typing import List, Dict


def validate_training_data_format(
    data_file: Path,
    model_path: str,
    sample_size: int = 100
) -> bool:
    """Validate training data uses correct chat template format.

    Compares training data format with tokenizer's chat template
    by reconstructing prompts and checking they match.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    import jsonlines
    with jsonlines.open(data_file) as reader:
        examples = list(reader)[:sample_size]

    mismatches = []

    for i, example in enumerate(examples):
        # Reconstruct what prompt SHOULD be
        messages = example.get("messages", [])
        if not messages:
            continue

        expected_prompt = tokenizer.apply_chat_template(
            messages[:-1],  # All except assistant response
            tokenize=False,
            add_generation_prompt=True,
        )

        # Extract actual prompt from example
        actual_prompt = "".join([
            msg["content"] for msg in messages[:-1]
        ])

        if expected_prompt != actual_prompt:
            mismatches.append({
                "index": i,
                "expected": expected_prompt[:100],
                "actual": actual_prompt[:100],
            })

    if mismatches:
        print(f"❌ Found {len(mismatches)} format mismatches:")
        for m in mismatches[:5]:  # Show first 5
            print(f"  Example {m['index']}:")
            print(f"    Expected: {m['expected']}...")
            print(f"    Actual: {m['actual']}...")
        return False

    print(f"✅ All {len(examples)} examples match tokenizer chat template")
    return True


# Usage in training pipeline:
def train_phase26():
    # Validate BEFORE training
    if not validate_training_data_format(
        data_file=Path("data/phase26_merged/train.jsonl"),
        model_path="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    ):
        raise ValueError("Training data format mismatch! Fix before training.")

    # Now train with confidence...
```

**Pros:**
- ✅ Catches format issues before expensive training
- ✅ No runtime overhead (pre-training check only)
- ✅ Validates actual training data, not just test scripts
- ✅ Can be added to CI/CD pipeline

**Cons:**
- ❌ Only catches training data issues, not test script issues
- ❌ Requires parsing training data format
- ❌ May have false positives if data format is complex

**When to use:** Add this to `scripts/train_phase*.sh` as a pre-flight check.

---

## Recommendation

**Use a combination:**

1. **Primary solution (Option A):** Always use `tokenizer.apply_chat_template()`
   - Update all test scripts to use shared `format_prompt_with_tokenizer()` utility
   - This prevents the bug at the source

2. **Pre-training check (Option C):** Add format validator to training scripts
   - Run before every training job
   - Catches data format issues early
   - No runtime overhead

3. **Optional validation (Option B):** Only during development
   - Enable validation in test scripts with `--validate` flag
   - Disable in production (zero overhead)
   - Useful for catching accidental manual formatting

**Implementation plan:**

```python
# src/punie/agent/prompt_utils.py (NEW FILE)
from pathlib import Path
from transformers import AutoTokenizer


_tokenizer_cache = {}  # Cache tokenizers to avoid reloading


def get_tokenizer(model_path: str | Path):
    """Get tokenizer from cache or load."""
    path_str = str(model_path)
    if path_str not in _tokenizer_cache:
        _tokenizer_cache[path_str] = AutoTokenizer.from_pretrained(model_path)
    return _tokenizer_cache[path_str]


def format_prompt(
    query: str,
    model_path: str | Path,
    system_message: str = "You are Punie, an AI coding assistant...",
) -> str:
    """Format prompt using model's chat template.

    This is the ONLY way to format prompts. Do not use manual string formatting.

    Args:
        query: User query
        model_path: Path to model directory (for loading tokenizer)
        system_message: System message (default: Punie assistant)

    Returns:
        Formatted prompt string in model's chat format
    """
    tokenizer = get_tokenizer(model_path)

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": query},
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


# Update all test scripts to use this:
# OLD:
# prompt = f"User: {query}\nAssistant:"

# NEW:
# prompt = format_prompt(query, model_path)
```

## Performance Impact

**Option A (tokenizer.apply_chat_template):**
- Overhead: ~0.01ms per prompt (negligible)
- One-time tokenizer load: ~50ms
- **Verdict:** No meaningful impact

**Option B (Pydantic validation):**
- Overhead: ~0.1-0.5ms per prompt
- Impact on 25-query suite: +2.5-12.5ms total
- **Verdict:** Acceptable for testing, disable in production

**Option C (pre-training validation):**
- Overhead: ~1-5 seconds before training starts
- Zero runtime overhead
- **Verdict:** Free insurance

## Conclusion

**The bug was caused by not using the tokenizer API, not by lack of validation.**

The solution is to:
1. Always use `tokenizer.apply_chat_template()` (Option A)
2. Add pre-training format check (Option C)
3. Optionally add runtime validation during development (Option B)

Pydantic validation is useful for defense-in-depth, but the real fix is **architectural: use the tokenizer API consistently everywhere.**

## Files to Update

1. `src/punie/agent/prompt_utils.py` - Create shared formatting utility
2. `scripts/test_phase*.py` - Update to use `format_prompt()`
3. `src/punie/training/format_validator.py` - Add pre-training check
4. `scripts/train_phase*.sh` - Add format validation step
5. `tests/test_prompt_consistency.py` - Add tests that verify train/test consistency

**Bottom line:** This is worth doing, but focus on Option A (use tokenizer API) first, then add Options B/C as defense-in-depth.
