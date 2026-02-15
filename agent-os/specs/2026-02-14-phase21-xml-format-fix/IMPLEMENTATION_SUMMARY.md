# Phase 21: Tool-Calling Format Fix - Implementation Summary

**Date:** 2026-02-14
**Status:** Ready for Training

## Problem Statement

Phase 21 profiling revealed 40% accuracy (2/5) through the PydanticAI → mlx_lm.server pipeline. Root cause: **training data format mismatch**.

- **Model trained on:** ````json` code fences (`{"name": "tool", "arguments": {...}}`)
- **Server expects:** Qwen3-Coder XML format (`<tool_call><function=name><parameter=key>value</parameter></function></tool_call>`)
- **Server detection:** Token-level check for `<tool_call>` (ID 151657) never triggers
- **Result:** No `tool_calls` in API response → PydanticAI treats as text → no tools executed

## Implementation Completed

### ✅ Task 1: Training Data Converter

**File:** `scripts/convert_to_xml_format.py`

Converts Phase 8 training data from JSON code fences to XML format:

```python
# OLD FORMAT
I'll use the run_command tool.

```json
{"name": "run_command", "arguments": {"command": "grep -r ..."}}
```

# NEW FORMAT
I'll use the run_command tool.

<tool_call>
<function=run_command>
<parameter=command>
grep -r ...
</parameter>
</function>
</tool_call>
```

**Results:**
- Converted 683 examples (546 train, 68 valid, 69 test)
- 70.7% with tool calls, 29.3% direct answers
- Output: `data/phase8_xml_format/`

### ✅ Task 2: Update Data Generation Scripts

**Files Updated:**
- `scripts/generate_domain_examples.py:30-51` - `create_messages()` now uses XML
- `scripts/convert_training_data.py:22-43` - `format_tool_call()` now uses XML

**Changes:**
- Tool calls: JSON code fence → XML format
- Tool results: `"Tool result: ..."` → `"<tool_response>\n...\n</tool_response>"`

### ✅ Task 3: Training Script

**File:** `scripts/train_phase21_xml.sh`

Full pipeline:
1. LoRA training (500 iters, batch_size 1, lr 1e-4, 8 layers)
2. Fuse to float16 (dequantize to preserve LoRA deltas)
3. Quantize to 5-bit (proven in Phase 20)

**Expected runtime:** ~2 hours

### ✅ Task 4: Server Pipeline Test

**File:** `scripts/test_server_pipeline.py`

**Critical missing test** that validates end-to-end:
1. Starts mlx_lm.server with fused model
2. Sends requests via OpenAI API with `tools` parameter
3. Verifies `tool_calls` appear in response (not just raw text)
4. Runs 5-query discrimination test through real pipeline

This tests: Model → `<tool_call>` token → server parser → structured response → PydanticAI

### ✅ Task 5: Update Direct Model Test

**File:** `scripts/test_single_model.py`

Updated `is_tool_response()` to check for `<tool_call>` instead of ````json`

## Verification Status

✅ All scripts pass type checking (`uv run ty check`)
✅ All scripts pass linting (`uv run ruff check`)
✅ Data conversion completed (683 examples)
✅ XML format samples inspected and verified

## Next Steps

### 1. Start Training (Task 3)

```bash
./scripts/train_phase21_xml.sh
```

**Expected outcomes:**
- LoRA adapter learns to generate `<tool_call>` XML tokens
- Model maintains discrimination ability (tool vs direct)
- Validation loss converges (target: <1.0)

### 2. Test Server Pipeline (Task 4)

```bash
uv run python scripts/test_server_pipeline.py
```

**Success criteria:**
- 100% accuracy (5/5) through full pipeline
- API response includes structured `tool_calls` field
- Tool calls parsed correctly by mlx_lm.server

### 3. Profile Latency (Task 6)

```bash
uv run python scripts/profile_latency.py
```

**Expected:**
- 100% accuracy (5/5)
- Latency similar to Phase 20 (~3-4s per query)

### 4. Benchmark Speculative Decoding (Task 6)

```bash
uv run python scripts/benchmark_speculative.py
```

**Now meaningful** since tool calls actually work!

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Model doesn't learn `<tool_call>` token | Low | Token ID 151657 in base vocab; base model already knows this format |
| 5-bit quantization destroys XML | Low | 5-bit proven in Phase 20; XML uses base vocab tokens (stronger signal) |
| Direct-answer quality regresses | Low | Direct-answer examples unchanged in conversion |
| Training takes too long | Low | Same config as Phase 8 (~2 hours proven) |

## Expected Impact

**Before (Phase 20):**
- Pipeline accuracy: 40% (2/5)
- Tool-calling queries: All fail
- Root cause: Format mismatch

**After (Phase 21):**
- Pipeline accuracy: 100% (5/5)
- Tool-calling queries: All succeed
- Format: Aligned (XML throughout)

## Files Modified

### Created
- `scripts/convert_to_xml_format.py` - Data converter
- `scripts/train_phase21_xml.sh` - Training pipeline
- `scripts/test_server_pipeline.py` - End-to-end test
- `data/phase8_xml_format/` - Converted training data

### Updated
- `scripts/generate_domain_examples.py` - XML format for future data
- `scripts/convert_training_data.py` - XML format for future data
- `scripts/test_single_model.py` - XML detection

## Evidence Trail

1. **Training data analysis:** Phase 8 data uses ````json` format
2. **Chat template inspection:** Qwen3-Coder expects XML format (line 80)
3. **Server code review:** Token-level detection at `server.py:1426`
4. **PydanticAI behavior:** No `tool_calls` → treats as text
5. **Phase 20 gap:** `test_single_model.py` uses direct generation (bypasses server)

## References

- [mlx-lm #613](https://github.com/ml-explore/mlx-lm/issues/613) - Tool call stop token issues
- [mlx-lm #607](https://github.com/ml-explore/mlx-lm/issues/607) - Server crashes on non-JSON tool_calls
- [PydanticAI #160](https://github.com/pydantic/pydantic-ai/issues/160) - Custom parsing for local models
- `docs/research/tool-calling-investigation.md` - Punie's tool-calling research (Feb 11)

---

**Status:** ✅ Implementation complete, ready for training
**Next action:** Run `./scripts/train_phase21_xml.sh` to start 2-hour training pipeline
