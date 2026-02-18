# Phase 37b Validation Checklist

## Pre-Validation Setup

- [ ] Start Ollama server: `ollama serve`
- [ ] Verify Devstral is loaded: `ollama list | grep devstral`
- [ ] If not loaded: `ollama pull devstral`

## Run Validation

```bash
uv run python scripts/validate_zero_shot_code_mode.py --model devstral 2>&1 | tee validation_output_phase37b.txt
```

## Expected Results

### API Errors (should drop from 53% to ~0%)

Phase 37 (before fixes):
```
Query: "Run ruff" → ❌ API error: invalid message content type: <nil> (2.11s)
Query: "Check git status" → ❌ API error: invalid message content type: <nil> (2.29s)
Query: "Run pytest" → ❌ API error: invalid message content type: <nil> (2.18s)
```

Phase 37b (after fixes):
```
Query: "Run ruff" → ✅ Should complete successfully
Query: "Check git status" → ✅ Should complete successfully
Query: "Run pytest" → ✅ Should complete successfully
```

### Tool Calling (should improve from 17%)

Baseline: 3/17 (17%)
Target: 10+/17 (60%+)

### Direct Answers (should remain 100%)

Should stay: 5/5 (100%)

## Success Criteria

- ✅ API errors drop to ≤2/22 (9%)
- ✅ Tool calling improves to ≥10/17 (60%)
- ✅ Direct answers remain 5/5 (100%)
- ✅ Overall accuracy ≥15/22 (68%) — up from 8/22 (36%)

## Comparison Table Template

| Category | Phase 37 (before) | Phase 37b (after) | Change |
|----------|-------------------|-------------------|--------|
| Direct answers | 5/5 (100%) | ?/5 (?%) | ? |
| API errors | 9/17 (53%) | ?/17 (?%) | ? |
| Tool calling (no errors) | 3/17 (17%) | ?/17 (?%) | ? |
| Code Mode | 0/17 (0%) | ?/17 (?%) | ? |
| **Overall** | **8/22 (36%)** | **?/22 (?%)** | **?** |

## Post-Validation

- [ ] Update `docs/phase37-devstral-zero-shot-results.md` with Phase 37b section
- [ ] Update `MEMORY.md` with results
- [ ] Update comparison table in this file
- [ ] Decide on Phase 38 direction based on results
