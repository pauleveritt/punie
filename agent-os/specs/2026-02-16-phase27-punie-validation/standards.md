# Phase 27 Punie Validation - Standards

This spec follows Agent OS standards for verification and testing.

## agent-verification

**Standard:** `agent-os/standards/agent-verification.md`

**Application:**
- ✅ Create validation script before running tests
- ✅ Test real model behavior, not mocks
- ✅ Use representative queries across categories
- ✅ Document pass/fail criteria clearly
- ✅ Measure performance (load time, response time)
- ✅ Compare to baseline (Phase 27 benchmark: 2.33s avg)

**Specific to this spec:**
- Smoke test has 10 queries covering 2 categories:
  1. Model/Tool Initialization (5 queries)
  2. Representative Tool Execution (5 queries)
- Pass criteria: 10/10 (100%)
- Performance tolerance: ±20% of Phase 27 benchmark
- Baseline: 2.33s average generation time (Phase 27)

## function-based-tests

**Standard:** `agent-os/standards/function-based-tests.md`

**Application:**
- ✅ Write test functions, never test classes
- ✅ Use descriptive function names (test_model_loads, test_simple_query)
- ✅ One assertion per test function (single responsibility)
- ✅ Use async def for async tests
- ✅ Clean up resources in try/finally blocks

**Specific to this spec:**
```python
# ✅ CORRECT: Function-based async test
async def test_model_loads():
    """Verify Phase 27 model loads in local mode."""
    agent, client = create_local_agent("local", workspace=tmp_dir)
    try:
        assert agent is not None
        assert isinstance(client, LocalClient)
    finally:
        # Cleanup if needed
        pass

# ❌ WRONG: Class-based test
class TestPunieAsk:
    def test_model_loads(self):
        ...
```

## prompt-format-consistency

**Critical Rule:** Always use `punie.agent.prompt_utils.format_prompt()`

**Why this matters:** Phase 26.1 revealed a 60-point accuracy drop (28% → 88%) when using plain text prompts instead of the tokenizer's ChatML template.

**Application:**
```python
# ✅ CORRECT: Always use this
from punie.agent.prompt_utils import format_prompt

prompt = format_prompt("Check types in src/", model_path)

# ❌ WRONG: Never do this!
# prompt = f"User: {query}\nAssistant:"
# This causes train/test format mismatch!
```

**Reference:** `docs/research/prompt-format-consistency.md`

## Additional Project Standards

### Python 3.14
Use modern language features:
- Type hints with PEP 750 t-strings
- Structural pattern matching (match/case)
- Exception groups (except*)

### Astral Tools
- Use `astral:ruff` for linting
- Use `astral:ty` for type checking
- Use `astral:uv` for package management

### No Auto-Commit
Never create commits without explicit user request.

### Async Patterns
```python
# ✅ CORRECT: Proper async cleanup
async def test_with_cleanup():
    agent, client = create_local_agent("local", workspace)
    try:
        result = await agent.run("query", deps=ACPDeps(...))
        assert result.output
    finally:
        # Cleanup resources
        await client.cleanup()

# ❌ WRONG: No cleanup
async def test_no_cleanup():
    agent, client = create_local_agent("local", workspace)
    result = await agent.run("query", deps=ACPDeps(...))
    # Hanging tasks!
```

## Verification Checklist

Before merging Phase 27 validation:

- [ ] All test functions use async def (no classes)
- [ ] All prompts use format_prompt() utility
- [ ] Pass criteria documented (10/10 = 100%)
- [ ] Performance baseline compared (±20% tolerance)
- [ ] Resources cleaned up (no hanging tasks)
- [ ] `astral:ty` passes (type checking)
- [ ] `astral:ruff` passes (linting)
- [ ] All 582 existing tests still pass
- [ ] Smoke test passes (10/10)
- [ ] Documentation created (results.md)
