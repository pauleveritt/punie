# Phase 43a Standards

## agent-verification

All new code must pass:
- `astral:ruff` (linting + formatting)
- `astral:ty` (type checking)
- `uv run pytest tests/` (no regressions)

## function-based-tests

Tests are always function-based, never class-based. See `tests/` for examples.

```python
# ✅ Correct
def test_phase43a_results_doc_exists():
    path = Path("docs/research/phase43a-coder30b-results.md")
    assert path.exists()

# ❌ Wrong
class TestPhase43a:
    def test_results_doc(self):
        ...
```

## prompt-format-consistency

**CRITICAL:** All prompt formatting must use `punie.agent.prompt_utils.format_prompt()`.
Never use manual string formatting. This is the Phase 26.1 lesson — wrong format = 60-point
accuracy drop.

```python
# ✅ CORRECT
from punie.agent.prompt_utils import format_prompt
prompt = format_prompt("Check types in src/", model_path)

# ❌ WRONG
prompt = f"User: {query}\nAssistant:"
```

## training-data-unchanged

Phase 43a uses `data/phase33_merged` unchanged. Do not regenerate, reshuffle, or modify the
training data. The goal is to reproduce the Phase 33b baseline with Phase 43 naming.

## eval-script-reuse

The eval script `scripts/run_phase33_direct_eval.py` is reused for Phase 43a eval.
It accepts `--model` argument to specify any model path; model ID detection is not hardcoded.

## pre-registered-success-criteria

Success criteria must be registered BEFORE running the experiment. The criteria for Phase 43a:

| Category | Phase 33b Baseline | Phase 43a Target |
|----------|--------------------|------------------|
| text_tools | 100% | ≥100% |
| validation | 100% | ≥100% |
| git | 100% | ≥100% |
| cst | 100% | ≥100% |
| lsp | 90% | ≥90% |
| domain | 60% | >60% (target improvement) |
| multi_tool | 35% | >35% (target improvement) |
| **Overall** | **82.4%** | **≥82.4%** |

Reporting partial results (e.g., "domain improved but overall dropped") is not passing.
The overall ≥82.4% gate is a hard requirement.
