# Phase 24: Add ruff + pytest Typed Tools + Expand Domain Data

## Goal

Add two more typed tools (ruff_check, pytest_run) following the typecheck pattern, and significantly expand domain-specific training data by mining tdom repository and applying a structured src/docs strategy.

## Context

Phase 23 established:
- First typed tool: `typecheck()` returning `TypeCheckResult`
- 757 training examples (707 Phase 22 + 50 ty)
- 84% validation loss reduction
- Model: Qwen3-Coder-30B-A3B-Instruct-4bit (23 GB, 5-bit)

Phase 24 will:
1. Add ruff and pytest as typed tools
2. Mine tdom repository for domain examples
3. Use structured approach: src/ for code, docs/ for concepts
4. Target: ~1000+ training examples

This prepares for Phase 25 (7B model experiment) by giving smaller model more training signal.

---

## Part 1: Implement Typed Tools

### Task 1: Create RuffResult Pydantic Model

**File:** `src/punie/agent/typed_tools.py` (add to existing)

**Models:**
```python
class RuffViolation(BaseModel):
    file: str
    line: int
    column: int
    code: str  # e.g., "E501", "F841"
    message: str
    severity: str  # "error" | "warning"

class RuffResult(BaseModel):
    success: bool  # True if no errors
    error_count: int
    warning_count: int
    violations: list[RuffViolation]

def parse_ruff_output(output: str) -> RuffResult:
    """Parse ruff --output-format json to RuffResult."""
    ...
```

**Tests:** `tests/test_typed_tools.py` (add to existing)
- Validation tests for RuffViolation and RuffResult
- Parser tests (empty, errors, warnings, malformed)

### Task 2: Create TestResult Pydantic Model

**File:** `src/punie/agent/typed_tools.py` (add to existing)

**Models:**
```python
class TestFailure(BaseModel):
    test_id: str  # e.g., "tests/test_foo.py::test_bar"
    message: str
    traceback: str | None = None

class TestResult(BaseModel):
    success: bool  # True if all tests passed
    passed: int
    failed: int
    skipped: int
    total: int
    failures: list[TestFailure]

def parse_pytest_output(output: str) -> TestResult:
    """Parse pytest --json-report output to TestResult."""
    ...
```

**Tests:** `tests/test_typed_tools.py` (add to existing)
- Validation tests for TestFailure and TestResult
- Parser tests (all pass, some fail, all fail, skipped)

### Task 3: Implement ruff_check() External Function

**Files to modify:**
- `src/punie/agent/monty_runner.py` - Add ruff_check to ExternalFunctions
- `src/punie/agent/toolset.py` - Implement sync_ruff_check bridge
- `src/punie/agent/stubs.py` - Add ruff_check stub
- `tests/test_monty_runner.py` - Add fake_ruff_check

**Implementation pattern (same as typecheck):**
```python
def sync_ruff_check(path: str) -> RuffResult:
    async def _run_ruff() -> RuffResult:
        term = await ctx.deps.client_conn.create_terminal(
            command="ruff",
            args=["check", path, "--output-format", "json"],
            ...
        )
        # terminal workflow
        ...
        return parse_ruff_output(output_resp.output)

    future = asyncio.run_coroutine_threadsafe(_run_ruff(), loop)
    return future.result(timeout=30)
```

### Task 4: Implement pytest_run() External Function

**Files to modify:**
- `src/punie/agent/monty_runner.py` - Add pytest_run to ExternalFunctions
- `src/punie/agent/toolset.py` - Implement sync_pytest_run bridge
- `src/punie/agent/stubs.py` - Add pytest_run stub
- `tests/test_monty_runner.py` - Add fake_pytest_run

**Implementation pattern:**
```python
def sync_pytest_run(path: str) -> TestResult:
    async def _run_pytest() -> TestResult:
        term = await ctx.deps.client_conn.create_terminal(
            command="pytest",
            args=[path, "--json-report", "--json-report-file=-"],
            ...
        )
        # terminal workflow
        ...
        return parse_pytest_output(output_resp.output)

    future = asyncio.run_coroutine_threadsafe(_run_pytest(), loop)
    return future.result(timeout=30)
```

### Task 5: Update System Prompt

**File:** `src/punie/agent/config.py`

Add guidelines for new tools:
- When to use ruff_check() vs run_command("ruff", ...)
- When to use pytest_run() vs run_command("pytest", ...)
- Explain structured return types

---

## Part 2: Expand Domain Training Data

### Data Mining Strategy

**Repositories:**
1. `~/projects/t-strings/svcs-di` (existing)
2. `~/projects/t-strings/tdom-svcs` (existing)
3. **`~/projects/t-strings/tdom`** (new!)

**Mining approach:**
- **src/**: Mine for code examples (read files, analyze structure, tool usage)
- **docs/**: Mine for conceptual questions (what is X, how does Y work, when to use Z)
- **tests/**: Mine for testing patterns (pytest examples)

### Task 6: Mine tdom Repository

**Script:** `scripts/mine_tdom_examples.py`

**Categories to generate:**

1. **Code exploration (15 examples from src/):**
   - "Show me the tdom component architecture"
   - "Find all view functions in src/tdom/"
   - "What classes inherit from Component?"
   - "Show me how tdom renders HTML"

2. **Testing patterns (15 examples from tests/):**
   - "Run tests in tests/test_components.py"
   - "Show me examples of tdom component tests"
   - "Fix failing test in test_rendering.py"

3. **Conceptual questions (15 examples from docs/):**
   - "What is a tdom component?"
   - "How does tdom differ from other template engines?"
   - "Explain tdom's rendering model"
   - "When should I use tdom vs Jinja2?"

4. **Tool usage (10 examples):**
   - "Check types in src/tdom/" → typecheck()
   - "Lint tdom codebase" → ruff_check()
   - "Run tdom tests" → pytest_run()

**Output:** `data/tdom_training/tdom_examples.jsonl` (~55 examples)

### Task 7: Expand svcs-di Examples with src/docs Strategy

**Script:** `scripts/expand_svcs_di_examples.py`

Apply same strategy to existing svcs-di repo:
- Mine src/ for code examples (DI patterns, service registration)
- Mine docs/ for conceptual questions (what is DI, when to use svcs)
- Mine tests/ for testing patterns

**Target:** +30 examples → `data/svcs_di_expanded/examples.jsonl`

### Task 8: Expand tdom-svcs Examples with src/docs Strategy

**Script:** `scripts/expand_tdom_svcs_examples.py`

Apply strategy to tdom-svcs repo:
- Mine src/ for integration code (tdom + svcs patterns)
- Mine docs/ for conceptual questions (how to integrate, best practices)
- Mine tests/ for testing patterns

**Target:** +30 examples → `data/tdom_svcs_expanded/examples.jsonl`

---

## Part 3: Generate Typed Tool Training Data

### Task 9: Generate ruff Training Examples

**Script:** `scripts/generate_ruff_training_data.py`

**Categories (50 examples):**

1. **Simple lint check (15):**
   - "Check for lint errors in src/punie/agent/"
   - "Are there any unused imports in config.py?"
   - "Show me all F401 errors"

2. **Check-and-fix (15):**
   - "Fix all lint errors in factory.py"
   - "Remove unused imports from toolset.py"
   - Check → read → fix → verify pattern

3. **Lint-informed refactoring (10):**
   - "Refactor this function and ensure no lint errors"
   - "Split long function and check line length"

4. **Direct answers (10):**
   - "What does ruff error E501 mean?"
   - "What's the difference between F and E error codes?"
   - "Should I use ruff or pylint?"

**Output:** `data/ruff_training/ruff_examples.jsonl`

### Task 10: Generate pytest Training Examples

**Script:** `scripts/generate_pytest_training_data.py`

**Categories (50 examples):**

1. **Simple test run (15):**
   - "Run tests in tests/test_agent.py"
   - "Are there any failing tests?"
   - "Show me test results for monty_runner"

2. **Test-and-fix (15):**
   - "Fix the failing test in test_factory.py"
   - Test → read failure → fix → retest pattern

3. **Test-driven development (10):**
   - "Write a function and test it"
   - "Add test for edge case then implement"

4. **Direct answers (10):**
   - "What's the difference between pytest and unittest?"
   - "How do I use pytest fixtures?"
   - "What does pytest -xvs do?"

**Output:** `data/pytest_training/pytest_examples.jsonl`

---

## Part 4: Merge and Train

### Task 11: Merge All Training Data

**Script:** `scripts/merge_phase24_data.py`

**Inputs:**
- Phase 23: 757 examples
- tdom: ~55 examples
- svcs-di expanded: ~30 examples
- tdom-svcs expanded: ~30 examples
- ruff: 50 examples
- pytest: 50 examples

**Total:** ~972 examples (target: break 1000!)

**Additional synthetic examples to reach 1000:**
- 28 more multi-step workflows combining tools
- Examples using typecheck + ruff together
- Examples using all 3 typed tools in sequence

**Split:** 80/10/10
- Train: ~776 examples
- Valid: ~98 examples
- Test: ~98 examples

**Output:** `data/phase24_merged/`

### Task 12: Train Phase 24 Model

**Script:** `scripts/train_phase24.sh`

**Parameters:**
- Model: Qwen3-Coder-30B-A3B-Instruct-4bit
- Iterations: 600 (more data = more iterations)
- Batch size: 1
- Learning rate: 1e-4
- LoRA layers: 8

**Expected:**
- Training time: ~15-20 minutes
- Peak memory: ~21 GB
- Target val loss: <0.8 (similar to Phase 23)

**Scripts to create:**
- `scripts/train_phase24.sh` - Training pipeline
- `scripts/fuse_phase24.sh` - Fusion to float16
- `scripts/quantize_phase24_5bit.sh` - 5-bit quantization

### Task 13: Validate Phase 24 Model

**Script:** `scripts/test_phase24_model.py`

**Test categories:**

**A. Single-tool discrimination (8 queries):**
1. "Check types in src/punie/agent/" → typecheck()
2. "Lint src/punie/agent/" → ruff_check()
3. "Run tests in tests/" → pytest_run()
4. "What is a Protocol in Python?" → direct answer
5. "Show me the factory.py file" → read_file()
6. "What's the difference between ruff and pylint?" → direct answer
7. "Check for unused imports" → ruff_check()
8. "Are tests passing?" → pytest_run()

**Success:** 100% (8/8)

**B. Multi-step workflows (7 queries):**
1. "Fix all type errors in config.py" → typecheck → read → fix → verify
2. "Fix lint errors in factory.py" → ruff → read → fix → verify
3. "Fix the failing test" → pytest → read failure → fix → retest
4. "Make this file pass all checks" → typecheck + ruff + pytest
5. "Refactor this function cleanly" → read → write → typecheck → ruff
6. "Add a new function with tests" → write → pytest → fix until pass
7. "Check tdom component quality" → typecheck + ruff (domain-specific)

**Success:** 80% (6/7) - Allow 1 failure on complex multi-tool workflow

**C. Domain knowledge (5 queries):**
1. "What is dependency injection?" → direct answer (svcs-di knowledge)
2. "How does tdom rendering work?" → direct answer (tdom knowledge)
3. "Show me a tdom component example" → read_file from tdom
4. "Find DI service registration in svcs-di" → grep/search
5. "What's the relationship between tdom and tdom-svcs?" → direct answer

**Success:** 100% (5/5) - Should know domain concepts

**Overall target:** 19/20 queries (95%)

---

## Part 5: Prepare for Phase 25

### Task 14: Document Phase 24 Results

Update documentation:
- Training metrics (loss curves, perplexity)
- Test results (20-query validation)
- Model size and performance
- Comparison to Phase 23

### Task 15: Create Phase 25 Plan

**File:** `docs/phase25-plan.md`

Document Phase 25 approach:
- Use Phase 24's ~1000 examples
- Train Qwen2.5-Coder-7B-Instruct-4bit
- Same test suite (20 queries)
- Compare: accuracy, speed, memory
- Decision criteria for 7B vs 30B

---

## Success Criteria

### Code Implementation
- [x] RuffResult and TestResult models created
- [x] ruff_check() and pytest_run() implemented
- [x] All tests passing (update test count)
- [x] System prompt updated

### Training Data
- [x] tdom repository mined (~55 examples)
- [x] svcs-di expanded (~30 examples)
- [x] tdom-svcs expanded (~30 examples)
- [x] ruff examples generated (50)
- [x] pytest examples generated (50)
- [x] Total: 1000+ examples

### Training
- [x] Phase 24 model trained (600 iterations)
- [x] Val loss < 0.8
- [x] Model fused to float16
- [x] Model quantized to 5-bit (~23 GB)

### Validation
- [x] 100% single-tool discrimination (8/8)
- [x] 80%+ multi-step workflows (6/7)
- [x] 100% domain knowledge (5/5)
- [x] Overall: 95% (19/20)

---

## Files to Create

### Code (2 files)
1. `src/punie/agent/typed_tools.py` - Add RuffResult, TestResult, parsers
2. `tests/test_typed_tools.py` - Add tests for new models

### Scripts (8 files)
3. `scripts/mine_tdom_examples.py` - Mine tdom repository
4. `scripts/expand_svcs_di_examples.py` - Expand svcs-di with src/docs strategy
5. `scripts/expand_tdom_svcs_examples.py` - Expand tdom-svcs with src/docs strategy
6. `scripts/generate_ruff_training_data.py` - Generate ruff examples
7. `scripts/generate_pytest_training_data.py` - Generate pytest examples
8. `scripts/merge_phase24_data.py` - Merge all data
9. `scripts/train_phase24.sh` - Training pipeline
10. `scripts/test_phase24_model.py` - Validation tests

### Data (5 directories)
11. `data/tdom_training/` - tdom examples
12. `data/svcs_di_expanded/` - Expanded svcs-di examples
13. `data/tdom_svcs_expanded/` - Expanded tdom-svcs examples
14. `data/ruff_training/` - ruff examples
15. `data/pytest_training/` - pytest examples
16. `data/phase24_merged/` - Final merged dataset

### Documentation (2 files)
17. `docs/phase24-progress.md` - Progress tracking
18. `docs/phase25-plan.md` - Phase 25 plan

---

## Files to Modify

1. `src/punie/agent/monty_runner.py` - Add ruff_check, pytest_run
2. `src/punie/agent/toolset.py` - Add sync bridges
3. `src/punie/agent/stubs.py` - Add stubs
4. `src/punie/agent/config.py` - Update system prompt
5. `tests/test_monty_runner.py` - Add fake functions
6. `tests/test_execute_code.py` - Add fake functions
7. `agent-os/product/roadmap.md` - Mark Phase 24 complete, add Phase 25

---

## Estimated Timeline

**Part 1 (Typed Tools):** ~45 minutes
- Task 1-2: Models and parsers (15 min)
- Task 3-4: Implement functions (20 min)
- Task 5: Update system prompt (5 min)
- Testing: Continuous (5 min)

**Part 2 (Domain Data):** ~1 hour
- Task 6: Mine tdom (20 min)
- Task 7-8: Expand existing repos (30 min)
- Review and quality check (10 min)

**Part 3 (Typed Tool Data):** ~45 minutes
- Task 9: Generate ruff examples (20 min)
- Task 10: Generate pytest examples (20 min)
- Review (5 min)

**Part 4 (Training):** ~20 minutes
- Task 11: Merge data (5 min)
- Task 12: Train model (15 min - automated)

**Part 5 (Validation):** ~30 minutes
- Task 13: Test model (20 min - manual)
- Task 14-15: Documentation (10 min)

**Total: ~3.5 hours** (mostly automated training/fusion/quantization)

---

## Next Phase Preview

**Phase 25: Model Size Experiment**
- Train Qwen2.5-Coder-7B-Instruct-4bit with Phase 24's 1000+ examples
- Same test suite, compare accuracy/speed/memory
- If successful: 4x faster inference, 60% less memory
- Decision: Use 7B going forward or stick with 30B

**Phase 26: Domain-Specific Tools**
- Project structure analysis
- Dependency graph traversal
- Semantic search over codebase
- The "holy grail" - truly helpful coding assistant
