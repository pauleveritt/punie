# Phase 24: Add ruff + pytest Typed Tools + Expand Domain Data

## Context

Phase 23 established the typed tools pattern with `typecheck()` returning `TypeCheckResult`. Training data is at 757 examples with 84% val loss reduction. Phase 24 adds ruff and pytest as typed tools, mines real code from tdom/svcs-di/tdom-svcs repositories, and pushes training data past 1000 examples. This prepares for Phase 25 (7B model experiment) by giving the smaller model more training signal.

**User direction:** Full Phase 24 scope plus deep dive cleanup. Critical bugs only. Real file content from repos. This runs overnight autonomously.

---

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-14-phase24-ruff-pytest-training/` with:
- `plan.md` — This full plan
- `shape.md` — Scope, decisions, architecture
- `standards.md` — agent-verification, function-based-tests, fakes-over-mocks, frozen-dataclass-services
- `references.md` — Key files and patterns

---

## Task 2: Fix Critical Bugs

### Bug 1: Broken doctest in monty_runner.py (lines 126-129)
`ExternalFunctions` constructed with 3 args but needs 4+ (missing typecheck, and soon ruff_check/pytest_run). Failing doctest via Sybil.

**Fix:** Update docstring example to include all fields.

**File:** `src/punie/agent/monty_runner.py` lines 119-129

### Bug 2: execute_code missing from known_tools (toolset.py lines 588-596)
Tier 1 tool discovery silently omits Code Mode.

**Fix:** Add `"execute_code": execute_code` to `known_tools` dict.

**File:** `src/punie/agent/toolset.py` lines 588-596

**Verify:** `uv run pytest` — all tests pass including Sybil doctests.

---

## Task 3: Add RuffResult and TestResult Pydantic Models

**File:** `src/punie/agent/typed_tools.py` (extend existing)

### Ruff Models
```python
class RuffViolation(BaseModel):
    file: str
    line: int
    column: int
    code: str         # e.g., "E501", "F401"
    message: str
    fixable: bool

class RuffResult(BaseModel):
    success: bool
    violation_count: int
    fixable_count: int
    violations: list[RuffViolation]

def parse_ruff_output(output: str) -> RuffResult: ...
```

### Pytest Models
```python
class TestCase(BaseModel):
    name: str          # "tests/test_foo.py::test_bar"
    outcome: str       # "passed", "failed", "error", "skipped"
    duration: float
    message: str | None = None

class TestResult(BaseModel):
    success: bool
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float
    tests: list[TestCase]

def parse_pytest_output(output: str) -> TestResult: ...
```

Note: Parse pytest `-v --tb=short` text output (no JSON plugin needed).

---

## Task 4: Add Tests for New Models

Add to `tests/test_typed_tools.py` (extend existing, don't create new file):
- Validation tests for RuffViolation, RuffResult, TestCase, TestResult
- Parser tests: empty, violations, failures, malformed input
- ~14 new tests following existing TypeCheckResult test pattern

**Verify:** `uv run pytest tests/test_typed_tools.py -v`

---

## Task 5: Add ruff_check and pytest_run to Sandbox

### 5a: Extend ExternalFunctions (`monty_runner.py` lines 23-33)
Add `ruff_check: Callable[[str], RuffResult]` and `pytest_run: Callable[[str], TestResult]`

### 5b: Register in namespace (`monty_runner.py` ~line 143)
Add `"ruff_check"` and `"pytest_run"` to namespace dict

### 5c: Add sync bridges (`toolset.py` after line 347)
Follow `sync_typecheck` pattern: async inner function → terminal workflow → parse output → `run_coroutine_threadsafe`

### 5d: Update ExternalFunctions constructor (`toolset.py` ~line 350)
Add `ruff_check=sync_ruff_check, pytest_run=sync_pytest_run`

### 5e: Update ALL test fixtures
- `tests/test_monty_runner.py`: Add `fake_ruff_check`, `fake_pytest_run` + update fixture
- `tests/test_execute_code.py`: Add fake functions + update construction

---

## Task 6: Add Sandbox Tests for New Tools

In `tests/test_monty_runner.py`:
- `test_run_code_calls_ruff_check()`
- `test_run_code_ruff_check_with_violations()`
- `test_run_code_calls_pytest_run()`
- `test_run_code_pytest_run_with_failures()`
- `test_run_code_ruff_pytest_workflow()`

**Verify:** `uv run pytest tests/test_monty_runner.py tests/test_execute_code.py -v`

---

## Task 7: Update Stubs and System Prompt

### 7a: Add stubs (`stubs.py` after typecheck stub ~line 131)
Manual stubs for `ruff_check(path: str) -> RuffResult` and `pytest_run(path: str) -> TestResult` with docstrings explaining return fields.

### 7b: Update system prompt guidelines (`config.py` ~line 32)
Replace "For other tools (ruff, pytest), use run_command()" with:
- `ruff_check()` for linting → structured RuffResult
- `pytest_run()` for testing → structured TestResult

### 7c: Add stub tests (`test_stubs.py`)
Assert `ruff_check` and `pytest_run` appear in generated stubs.

**Verify:** `uv run pytest tests/test_stubs.py -v`

---

## Task 8: Run All Tests (Checkpoint)

`uv run pytest` — everything passes before generating training data.

---

## Task 9: Generate Ruff Training Data (50 examples)

**Script:** `scripts/generate_ruff_training_data.py`
**Output:** `data/ruff_training/ruff_examples.jsonl`
**Format:** `{"messages": [{"role": "user", ...}, {"role": "assistant", "<tool_call>...code using ruff_check()...</tool_call>"}]}`

**Categories:**
1. Simple lint checks (15): "Run ruff on src/", "Check for unused imports"
2. Fix violations (15): ruff_check → read → fix → ruff_check verify
3. Ruff + typecheck combined (10): "Check both lint and types"
4. Direct answers (10): "What is F401?", "Ruff vs pylint?"

---

## Task 10: Generate Pytest Training Data (50 examples)

**Script:** `scripts/generate_pytest_training_data.py`
**Output:** `data/pytest_training/pytest_examples.jsonl`

**Categories:**
1. Simple test runs (15): "Run tests in tests/", "Are tests passing?"
2. Test + fix workflows (15): pytest_run → read failure → fix → rerun
3. Full quality pipeline (10): typecheck + ruff_check + pytest_run combined
4. Direct answers (10): "What are pytest fixtures?", "Function tests vs class tests?"

---

## Task 11: Generate Domain Training Data from Real Repos (115+ examples)

**Script:** `scripts/generate_phase24_domain_data.py`
**Output:** `data/phase24_domain/domain_examples.jsonl`

**Approach:** Read ACTUAL files from repos, embed real code snippets in training examples.

**Repositories:**
- tdom: `~/projects/t-strings/tdom/tdom/` (source), `*_test.py` (tests), `docs/` (docs)
- svcs-di: `~/projects/t-strings/svcs-di/src/` (source), `docs/` (docs)
- tdom-svcs: `~/projects/t-strings/tdom-svcs/src/` (source), `docs/` (docs)

### tdom examples (~55):
- 15 code reading (nodes.py, processor.py, parser.py, escaping.py, etc.)
- 10 code search (grep for dataclasses, find test files, count functions)
- 10 test patterns (from *_test.py files)
- 10 concept questions (from docs/usage/*.md)
- 10 multi-step workflows (read + analyze, search + count)

### svcs-di examples (~30):
- 8 code reading, 7 search, 5 concepts, 5 test patterns, 5 workflows

### tdom-svcs examples (~30):
- 8 code reading, 7 search, 5 concepts, 5 test patterns, 5 workflows

---

## Task 12: Generate Multi-Step Workflow Data (28+ examples)

**Script:** `scripts/generate_phase24_workflows.py`
**Output:** `data/phase24_workflows/workflow_examples.jsonl`

**Categories:**
1. Lint + Fix + Verify (7): ruff_check → read → write → ruff_check
2. Test + Fix + Rerun (7): pytest_run → read → fix → pytest_run
3. Full Quality Pipeline (7): ruff_check + typecheck + pytest_run combined
4. Domain + Quality (7): Read real file → typecheck → ruff_check → report

---

## Task 13: Merge All Training Data

**Script:** `scripts/merge_phase24_data.py`
**Output:** `data/phase24_merged/` (train.jsonl, valid.jsonl, test.jsonl)

**Sources:**
- Phase 23: 757 examples
- Ruff: ~50
- Pytest: ~50
- Domain: ~115
- Workflows: ~28
- **Total: ~1000 examples**

**Split:** 80/10/10 with seed 42
**Format:** Convert messages → text (Qwen chat format) using Phase 23 pattern.

---

## Task 14: Train Phase 24 Model

**Script:** `scripts/train_phase24.sh` (single pipeline script)

**Parameters:**
- Model: Qwen3-Coder-30B-A3B-Instruct-4bit
- Iterations: 600 (more data than Phase 23's 500)
- Batch size: 1, LR: 1e-4, LoRA layers: 8

**Pipeline (automated):**
1. Train LoRA adapter → `adapters/phase24_ruff_pytest/`
2. Fuse to float16 → `fused_model_qwen3_phase24_ruff_pytest_f16/`
3. Quantize to 5-bit → `fused_model_qwen3_phase24_ruff_pytest_5bit/`

---

## Task 15: Create Test Script and Document Results

**Script:** `scripts/test_phase24_model.py`

**Test queries (20 total):**

**A. Single-tool discrimination (8):**
1. "Check types in src/" → typecheck()
2. "Lint src/punie/" → ruff_check()
3. "Run tests in tests/" → pytest_run()
4. "Read config.py" → read_file()
5. "What is dependency injection?" → direct answer
6. "Find all async functions" → run_command/grep
7. "What is F401?" → direct answer
8. "Check lint and types" → ruff_check + typecheck

**B. Multi-step workflows (7):**
1. "Full quality check: lint + types + tests"
2. "Fix ruff violations in config.py"
3. "Find failing tests and suggest fixes"
4. "Check types, fix errors, verify with tests"
5. "Count ruff violations per file"
6. "Read tdom files and check types"
7. "Run tests, read failures, fix code"

**C. Domain knowledge (5):**
1. "What are tdom nodes?" → direct answer
2. "How does svcs-di injection work?" → direct answer
3. "What is tdom-svcs middleware?" → direct answer
4. "When should I use Protocol vs ABC?" → direct answer
5. "How does tdom handle HTML escaping?" → direct answer

**Targets:**
- A: 100% (8/8)
- B: 80%+ (6/7)
- C: 100% (5/5)
- Overall: 95% (19/20)

**After validation:** Update diary, MEMORY.md, roadmap.

---

## Verification

1. `uv run pytest` — all tests pass (existing + new)
2. Training completes with val loss < 0.8
3. Model fused and quantized (~20-25 GB)
4. Test script passes targets (19/20 queries)

---

## Key Files

**Modify:**
- `src/punie/agent/typed_tools.py` — Add RuffResult, TestResult, parsers
- `src/punie/agent/monty_runner.py` — Extend ExternalFunctions, fix doctest
- `src/punie/agent/toolset.py` — Add sync bridges, fix known_tools
- `src/punie/agent/stubs.py` — Add ruff_check, pytest_run stubs
- `src/punie/agent/config.py` — Update system prompt guidelines
- `tests/test_typed_tools.py` — Add model tests
- `tests/test_monty_runner.py` — Add fakes and tests
- `tests/test_execute_code.py` — Update fixtures
- `tests/test_stubs.py` — Add stub tests

**Create:**
- `scripts/generate_ruff_training_data.py`
- `scripts/generate_pytest_training_data.py`
- `scripts/generate_phase24_domain_data.py`
- `scripts/generate_phase24_workflows.py`
- `scripts/merge_phase24_data.py`
- `scripts/train_phase24.sh`
- `scripts/test_phase24_model.py`

---

## Estimated Timeline

| Phase | Tasks | Time |
|-------|-------|------|
| Spec + bugs | 1-2 | 15 min |
| Typed tools code | 3-7 | 45 min |
| Test checkpoint | 8 | 5 min |
| Training data gen | 9-12 | 90 min |
| Merge + train | 13-14 | 25 min (training automated) |
| **Total** | | **~3.5 hours** |
