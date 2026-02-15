# Phase 23 Testing Checklist

## Pre-Testing Setup

### 1. Verify Model Files
```bash
# Check that all model files were created
ls -lh fused_model_qwen3_phase23_ty_5bit/
# Should contain: config.json, tokenizer files, weights.safetensors

# Check model size (should be ~20-25 GB for 5-bit)
du -sh fused_model_qwen3_phase23_ty_5bit/
```

### 2. Start Model Server
```bash
# Terminal 1: Start mlx_lm server
uv run python -m mlx_lm.server \
  --model fused_model_qwen3_phase23_ty_5bit \
  --port 8080

# Wait for "Server started" message
# First query will be slow (~20-30s warm-up)
```

## Testing Categories

### A. Single-Tool Discrimination (5 queries)

These test whether the model correctly chooses to call tools or answer directly.

#### Query 1: Type checking (tool call expected)
```
Query: "Check types in src/punie/agent/"
Expected: execute_code with typecheck("src/punie/agent/")
Success: Model calls typecheck(), not run_command("ty", ...)
```

#### Query 2: Type error details (tool call expected)
```
Query: "What type errors are in config.py?"
Expected: execute_code with typecheck("src/punie/agent/config.py")
Success: Model calls typecheck() and lists specific errors
```

#### Query 3: Direct answer (no tool call)
```
Query: "What is a Protocol in Python typing?"
Expected: Direct answer explaining Protocol
Success: No tool call, accurate explanation of Protocol
```

#### Query 4: File reading (tool call expected)
```
Query: "Show me the TypeCheckResult model"
Expected: execute_code with read_file("src/punie/agent/typed_tools.py")
Success: Model reads file and shows the Pydantic model
```

#### Query 5: Concept question (no tool call)
```
Query: "What's the difference between TypeCheckResult and TypeCheckError?"
Expected: Direct answer explaining the relationship
Success: No tool call, accurate explanation from training data
```

**Success Criteria:** 5/5 correct discrimination (100% accuracy)

### B. Multi-Step ty Workflows (5 queries)

These test whether the model can chain typecheck() with other tools.

#### Query 6: Check and iterate errors
```
Query: "Check types in stubs.py and list each error with its line number"
Expected:
  1. execute_code: result = typecheck("src/punie/agent/stubs.py")
  2. Iterate result.errors and format output
Success: Model accesses result.errors, result.error_count, etc.
```

#### Query 7: Check multiple files
```
Query: "Check types in both stubs.py and typed_tools.py"
Expected:
  1. execute_code: typecheck("src/punie/agent/stubs.py")
  2. execute_code: typecheck("src/punie/agent/typed_tools.py")
Success: Model makes two separate typecheck() calls
```

#### Query 8: Check-read-fix pattern
```
Query: "Fix type errors in factory.py"
Expected:
  1. execute_code: result = typecheck("src/punie/agent/factory.py")
  2. execute_code: content = read_file("src/punie/agent/factory.py")
  3. execute_code: write_file("...", fixed_content)
  4. execute_code: verify with typecheck() again
Success: Model follows check → read → fix → verify workflow
```

#### Query 9: Conditional workflow
```
Query: "If there are any type errors in config.py, show me the first one"
Expected:
  1. execute_code: result = typecheck("src/punie/agent/config.py")
  2. Check result.success or result.error_count
  3. If errors, access result.errors[0]
Success: Model uses TypeCheckResult fields for conditional logic
```

#### Query 10: Type-informed coding
```
Query: "Write a function that takes TypeCheckResult and returns error count"
Expected:
  1. execute_code: write_file with function using TypeCheckResult
  2. execute_code: typecheck to verify the new function
Success: Model writes type-correct code and validates it
```

**Success Criteria:** 4/5 correct workflows (80% accuracy)

### C. Comparison with Phase 22

Run the same 5-query test from Phase 22 to ensure no regression.

**Success Criteria:** 5/5 accuracy maintained

## Performance Benchmarks

### Latency
- First query (warm-up): ~20-30 seconds
- Subsequent typecheck queries: ~3-5 seconds
- Direct answers: ~1-2 seconds

### Memory
- Model loading: ~20-25 GB
- Peak inference: ~21-22 GB
- Stable operation: ~20 GB

## Success Thresholds

| Category | Target | Minimum |
|----------|--------|---------|
| Single-tool discrimination | 100% (5/5) | 80% (4/5) |
| Multi-step workflows | 80% (4/5) | 60% (3/5) |
| Phase 22 regression test | 100% (5/5) | 100% (5/5) |
| Warm-up latency | <30s | <60s |
| Query latency | <5s | <10s |

## Red Flags

Stop testing and investigate if:
- Model never calls typecheck() (uses run_command("ty") instead)
- Model doesn't access TypeCheckResult fields (treats as string)
- Validation loss > 1.5 at end of training
- Model size != ~20-25 GB for 5-bit
- Inference uses >30 GB memory
- Any Phase 22 tests fail

## Post-Testing

### If tests pass:
1. Update MEMORY.md with Phase 23 completion
2. Mark Task 10 and Task 11 as complete
3. Update roadmap to show Phase 23 complete
4. Document model location for future use
5. Clean up intermediate models (float16 if disk space needed)

### If tests fail:
1. Check training logs for issues
2. Verify data format was correct
3. Compare validation loss to Phase 22
4. Test with Phase 22 model to isolate regression
5. May need to retrain with adjusted data

## Model Artifacts

**Production model:** `fused_model_qwen3_phase23_ty_5bit/`
- Size: ~20-25 GB
- Format: 5-bit quantized
- Ready for mlx_lm.server

**Intermediate (can delete after testing):**
- `fused_model_qwen3_phase23_ty_f16/` (~57 GB)
- `adapters/phase23_ty/` (~0.5 GB - keep for reference)

**Training data:**
- `data/phase23_merged/` - Keep for reproducibility
- `data/ty_training/` - Keep for reference
