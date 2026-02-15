# Evidence References

## Memory Documentation

**Primary source:** `MEMORY.md` (lines 3-84)

**Sections:**
- Phase 23: Solidify Code Mode + ty Integration (lines 3-56)
  - Part 1: Solidify Phase 22 (lines 9-12)
  - Part 2: ty Integration (lines 14-20)
  - Task 11: End-to-End Validation (lines 22-32)
  - Files created (lines 34-40)

## Task Evidence

### Task 23.4: Update roadmap

**Evidence:**
- Phase 22 marked complete: `agent-os/product/roadmap.md` lines 1217-1360
- Phase 23 entry exists: `agent-os/product/roadmap.md` lines 1362-1449
- Phase 24 entry exists: `agent-os/product/roadmap.md` lines 1452+
- Flywheel documented: `docs/flywheel.md` (full file)

### Task 23.5: Validate Phase 22 e2e

**Evidence:**
- Validation script: `scripts/test_phase23_task11.py`
- Diary entry: `docs/diary/2026-02-15-phase23-task11-validation.md`
- Results: 73.3% overall (11/15 queries), 100% single-tool, 20% multi-step, 0% field access

### Task 23.6: Create TypeCheckResult

**Evidence:**
- Implementation: `src/punie/agent/typed_tools.py` lines 1-50
- Models defined:
  - `TypeCheckError` (Pydantic model for individual errors)
  - `TypeCheckResult` (Pydantic model with errors list, error_count, output)

### Task 23.7: Implement typecheck()

**Evidence:**
- External function definition: `src/punie/agent/monty_runner.py` lines 40-45
- ACP bridge: `src/punie/agent/toolset.py` lines 273-283 (`sync_typecheck`)
- Stub generation: `src/punie/agent/stubs.py` lines 30-50 (includes typecheck)
- Parser: `src/punie/agent/typed_tools.py` lines 52-80 (`parse_ty_output`)

### Task 23.8: Update system prompt

**Evidence:**
- Dynamic stubs connected: `src/punie/agent/config.py` line 180 (uses `get_stub_instructions()`)
- Core functions list: `src/punie/agent/stubs.py` lines 20-25 (includes typecheck)
- Function signature: `src/punie/agent/stubs.py` lines 30-35

**Before Phase 23:**
```python
# Hand-written Code Mode section
PUNIE_INSTRUCTIONS = """
...
Available functions:
- execute_code(code: str) -> str
"""
```

**After Phase 23:**
```python
# Dynamic stub generation
stub_instructions = get_stub_instructions()
PUNIE_INSTRUCTIONS = f"""
...
{stub_instructions}
"""
```

### Task 23.9: Generate ty training data

**Evidence:**
- Generator script: `scripts/generate_ty_training_data.py`
- Output location: `data/phase23_merged/` (50 ty examples)
- Example categories:
  - Simple type check (15 examples)
  - Check-and-fix workflows (15 examples)
  - Type-informed coding (10 examples)
  - Direct answers (10 examples)

### Task 23.10: Merge and retrain

**Evidence:**
- Training data: `data/phase23_merged/` (757 examples total)
  - 707 from Phase 22
  - 50 new ty examples
- Training script: `scripts/train_phase23.sh`
- Fusion script: `scripts/fuse_phase23.sh`
- Quantization script: `scripts/quantize_phase23_5bit.sh`
- Final model: `fused_model_qwen3_phase23_ty_5bit/` (20 GB)
- Training metrics:
  - Initial val loss: 3.727
  - Final val loss: 0.610 (84% reduction)
  - Final train loss: 0.420

### Task 23.11: Validate ty e2e

**Evidence:**
- Test script: `scripts/test_phase23_task11.py` (15-query validation suite)
- Results documented: `docs/diary/2026-02-15-phase23-task11-validation.md`
- Key findings:
  - Single-tool discrimination: 100% (5/5) ✅
  - Multi-step workflows: 20% (1/5) ❌
  - **Field access: 0% (0/4)** ❌ CRITICAL GAP
- Gap analysis: Model calls tools but never accesses structured fields
- Resolution: Led to Phase 26 field access training

## Flywheel Documentation

**File:** `docs/flywheel.md`

**Contents:**
- Three-component architecture diagram
- LLM agent (Code Mode sandbox)
- External functions (ACP bridge)
- Domain tools (ty, ruff, pytest)
- Five-layer training data flywheel:
  1. Plan (human writes spec)
  2. Code (model generates Python)
  3. Execute (sandbox + ACP)
  4. Collect (structured results)
  5. Refine (create training examples)

## Phase 26 Connection

**Context:** Phase 23 validation (task 23.11) discovered 0% field access rate.

**Evidence:**
- Phase 26 spec: `agent-os/specs/2026-02-15-phase26-field-access-training/`
- Phase 26 model: `fused_model_qwen3_phase26_5bit/` (19.5 GB)
- Improvement: 24% → 92% accuracy (+68%)
- Field access rate: 5% → 90% (+85%)

**Reference:** `MEMORY.md` Phase 26 section (lines 140-237)

## Verification Checklist

- [x] All 8 tasks have file/directory evidence
- [x] Memory claims match codebase reality
- [x] Validation scripts exist and were run
- [x] Model artifacts present (fused_model_qwen3_phase23_ty_5bit/)
- [x] Diary entries document findings
- [x] Phase 26 followed up on identified gaps
- [x] Flywheel architecture documented
- [x] No conflicting evidence found
