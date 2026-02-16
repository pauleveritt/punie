# Phase 26: Train Structured Field Access Patterns - Shape

## Problem Shape

### The Gap
Phase 23 achieved 100% tool calling accuracy but **0% field access rate**. The model learned to:
- ✅ Discriminate between tool-calling and direct-answer queries
- ✅ Call typed tools with correct arguments
- ❌ Access structured fields on typed tool results
- ❌ Use result data in conditional logic or loops

### Root Cause Analysis

**Symptom:** Model calls `result = typecheck("src/")` but never accesses `result.error_count` or `result.errors`

**Diagnosis:**
1. Phase 22-24 training data: Only ~4.5% of examples show field access
2. Phase 24 ruff/pytest examples: DO show field access but were **never trained** (merged but skipped)
3. Training examples focus on tool calling syntax, not result usage

**Impact:** Typed tools provide no benefit over raw text — structured data is completely ignored

### Success Pattern

We need the model to learn this pattern:
```python
# Call tool (Phase 23 already does this ✅)
result = typecheck("src/")

# Access fields (Phase 23 NEVER does this ❌)
if result.error_count > 0:
    print(f"Found {result.error_count} errors")
    for error in result.errors:
        print(f"  {error.file}:{error.line} - {error.message}")
```

## Data Architecture

### Training Data Composition (~977 examples)

| Source | Examples | Contains Field Access? | Format | Status |
|--------|----------|------------------------|--------|---------|
| Phase 22 base | 707 | No | Text (needs conversion) | Use |
| Phase 23 ty | 50 | Some (~4.5%) | Text (needs conversion) | Use |
| Phase 24 ruff/pytest | 100 | Yes (~30%) | Messages Format B | Convert to Format A |
| Phase 26 field access | 120 | Yes (100%) | Messages Format A | Generate |
| **Total** | **977** | **~22% field access** | **Unified Format A** | **Train** |

### Field Access Pattern Coverage

Phase 26 adds 120 examples covering 4 patterns:

**Pattern 1: Conditional Logic (30 examples)**
```python
result = typecheck("src/")
if result.error_count > 0:
    print(f"Found {result.error_count} errors")
```

**Pattern 2: Field Access + Formatting (30 examples)**
```python
result = ruff_check("src/")
print(f"Violations: {result.violation_count}")
print(f"Fixable: {result.fixable_count}")
```

**Pattern 3: Iteration (30 examples)**
```python
result = typecheck("src/")
for error in result.errors:
    print(f"{error.file}:{error.line} - {error.message}")
```

**Pattern 4: Multi-step Workflows (30 examples)**
```python
result = typecheck("src/")
if not result.success:
    first_error = result.errors[0]
    content = read_file(first_error.file)
    # Fix the error using file content
```

### Tool × Pattern Matrix

Each tool (typecheck, ruff_check, pytest_run) × each pattern = 10 examples

|  | typecheck() | ruff_check() | pytest_run() | Total |
|--|-------------|--------------|--------------|-------|
| Conditional | 10 | 10 | 10 | 30 |
| Formatting | 10 | 10 | 10 | 30 |
| Iteration | 10 | 10 | 10 | 30 |
| Multi-step | 10 | 10 | 10 | 30 |
| **Total** | **40** | **40** | **40** | **120** |

## Format Unification

### Format A (Target)

**Structure:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are Punie, an AI coding assistant..."
    },
    {
      "role": "user",
      "content": "Check types in src/"
    },
    {
      "role": "assistant",
      "content": "<tool_call><function=execute_code><parameter=code>\nresult = typecheck(\"src/\")\nif result.error_count > 0:\n    print(f\"Found {result.error_count} errors\")\n</parameter></function></tool_call>"
    }
  ]
}
```

**Key characteristics:**
- Messages format (not text format with `<|im_start|>`)
- System message in every example
- XML wrapper: `<tool_call><function=execute_code><parameter=code>`
- Python code with field access patterns

### Format B (Phase 24 ruff/pytest - needs conversion)

**Structure:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Run ruff on src/"
    },
    {
      "role": "assistant",
      "content": "<tool_call>\nresult = ruff_check(\"src/\")\nprint(f\"Violations: {result.violation_count}\")\n</tool_call>"
    }
  ]
}
```

**Differences from Format A:**
- No system message
- Bare `<tool_call>` (no XML wrapper)
- Otherwise identical Python code

**Conversion needed:**
1. Add system message
2. Wrap with `<function=execute_code><parameter=code>` XML

## Validation Strategy

### Pre-Training Checks

Use `run_pre_training_checks()` with:
```python
expected_patterns = (
    # typecheck fields
    "result.errors",
    "result.error_count",
    "result.warning_count",
    "result.success",
    # ruff_check fields
    "result.violations",
    "result.violation_count",
    "result.fixable_count",
    # pytest_run fields
    "result.tests",
    "result.passed",
    "result.failed",
)
```

**Pass criteria:** All patterns must appear at least once in merged data

### Post-Training Validation

25-query validation suite:

| Category | Queries | Pattern | Target Accuracy |
|----------|---------|---------|-----------------|
| A. Single-tool discrimination | 5 | Tool vs direct answer | 100% |
| B. Conditional logic | 5 | if result.error_count > 0: | 80% |
| C. Field access | 5 | print(result.violations[0].code) | 80% |
| D. Iteration | 5 | for error in result.errors: | 80% |
| E. Multi-step workflows | 5 | Check → access → read_file | 60% |

**Overall target:** 80%+ (20/25)
**Critical metric:** Field access rate ≥80% (vs 0% baseline)

## Training Configuration

- **Iterations:** 500 (proven sufficient in Phase 23)
- **Batch size:** 1 (stable memory usage)
- **Learning rate:** 1e-4 (standard)
- **LoRA layers:** 8 (balance between quality and training time)
- **Quantization:** 6-bit (proven optimal in Phase 8)
- **Expected loss:** Final val loss < 1.0 (Phase 23 achieved 0.610)

## Risk Assessment

**High Risk:**
- Signal too weak (only 22% of data shows field access) → Mitigation: Can upsample Phase 26 examples 2x if needed

**Medium Risk:**
- Direct answer regression (adding 120 tool examples may shift distribution) → Mitigation: Monitor Category A in validation

**Low Risk:**
- Training convergence (known working configuration)
- Format conversion errors (can validate with parser check)
