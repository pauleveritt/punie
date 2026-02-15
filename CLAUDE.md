# Claude Instructions for Punie

Punie is an experimental AI coding agent that delegates tool execution to PyCharm via the Agent Communication Protocol (ACP).

## Project Standards

- Use Astral tools directly via skills (`astral:ruff`, `astral:ty`, `astral:uv`), not justfile recipes
- Write function-based tests, never classes
- Use Sybil for doctest integration in README.md and docstrings

## Agent OS Integration

This project uses Agent OS for standards, skills, and commands:
- Standards in `agent-os/standards/`
- Skills in `agent-os/skills/`
- Commands in `agent-os/commands/`
- Roadmap in `agent-os/product/roadmap.md`
- Specs in `agent-os/specs/`

## Development Workflow

- **No auto-commit**: Always ask before creating commits
- **Verification**: Use `astral:ruff` and `astral:ty` skills for quality checks
- **Testing**: Run `uv run pytest` directly, not `just test`
- **Documentation**: Markdown files (MyST) in `docs/`, built with Sphinx + Furo

## Prompt Formatting Standards

**CRITICAL**: When writing test scripts or validation tools that format prompts for model inference, **always use `punie.agent.prompt_utils.format_prompt()`**. Never use manual string formatting.

```python
# ✅ CORRECT: Always use this
from punie.agent.prompt_utils import format_prompt

prompt = format_prompt("Check types in src/", model_path)

# ❌ WRONG: Never do this!
# prompt = f"User: {query}\nAssistant:"
# This causes train/test format mismatch and 60+ point accuracy drop!
```

**Why this matters**: Phase 26.1 revealed that using plain text prompts instead of the tokenizer's ChatML template caused a 60-point accuracy drop (28% → 88%). The model is trained using `tokenizer.apply_chat_template()`, so validation scripts must use the exact same format.

**Key lesson**: Train/test consistency in prompt formatting is critical. Always use the shared utility.

See `docs/research/prompt-format-consistency.md` for detailed analysis.

## Python Version

This project uses Python 3.14 for modern language features.
