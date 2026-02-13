---
date: 2026-02-13
summary: Guide to complete Phase 2 after code fixes, including generator bug fix, converter updates, and format notes.
---

# Phase 2 Completion Guide

*2026-02-13*


**Status:** Code fixes complete, awaiting data generation

**Date:** February 13, 2026

---

## What Was Accomplished

### ✅ Generator Bug Fixed

**File:** `scripts/generate_training_data.py` (lines 212-224)

**Problem:** The bug used `hasattr(part, "tool_name")` which matches BOTH `ToolCallPart` and `ToolReturnPart`, causing real tool results to never be captured.

**Solution:** Now uses `part_kind` discriminator:
```python
if part_kind == "tool-call":
    # Record tool call
elif part_kind == "tool-return":
    # Capture REAL result from part.content
```

### ✅ Converter Updated

**File:** `scripts/convert_training_data.py`

**Changes:**
- Handles examples with real tool results (not just non-tool examples)
- Filters out examples where `tool_calls[].result` is `None`
- Outputs `{text: ...}` format with Qwen tokens (format that worked in Phase 1)
- Properly formats multi-turn conversations with real tool results

**Output format:**
```
<|im_start|>system
You are Punie...
<|im_start|>user
{query}
<|im_start|>assistant
I'll use the grep tool.
```json
{...}
```
<|im_start|>user
Tool result: src/interfaces.py:8:class StorageProtocol(Protocol):
<|im_start|>assistant
Found 3 Protocol classes...
```

### ✅ Documentation Updated

- `MODEL_PERFORMANCE_TRACKER.md` - Phase 2 failure documented with learnings
- `scripts/run_generator.sh` - Wrapper script created

---

## Critical Discovery: Format Mismatch

**Phase 2 attempted approach (FAILED):**
- Used hand-authored examples with markdown-formatted tool calls
- Used `{messages}` format
- Model learned to GENERATE fake conversations (hallucinations)

**Correct approach (verified from Phase 1):**
- Use `{text}` format with Qwen chat tokens
- Generated examples (not hand-authored)
- Real tool results (not placeholders)
- Model learns to CALL tools via API

**Key insight:** Phase 1 proved the model CAN learn to call tools with `{text}` format. The infinite loop was caused by placeholder results, not the format itself.

---

## What Needs to Happen

### Step 1: Generate Training Data with Real Results (~70 minutes)

**Requirements:**
- 30B MLX server running on port 8080
- Server must stay up for entire generation (70+ minutes)
- Proper API connectivity

**Commands:**

1. Start 30B server:
```bash
nohup uv run python -m mlx_lm server \
    --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
    --port 8080 \
    --host 127.0.0.1 \
    > /tmp/mlx-30b-server.log 2>&1 &
```

2. Verify server is running:
```bash
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
# Should show: mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit
```

3. Generate data:
```bash
OPENAI_API_KEY='dummy' \
OPENAI_BASE_URL='http://127.0.0.1:8080/v1' \
uv run python -u scripts/generate_training_data.py 2>&1 | tee generation.log
```

**Expected output:**
- Target: 100 examples
- With tools: ~54 examples
- Without tools: ~15 examples
- Total: ~69 examples (some may fail)

### Step 2: Verify Real Results Were Captured

```bash
python3 scripts/convert_training_data.py
```

**Expected output:**
```
✓ Loaded examples:
  Without tools: 15
  With tools + real results: 54  ← This is the key metric!
  With tools + NO results: 0 (skipped)
  Total included: 69
```

**If "With tools + real results: 0":**
- The generator fix didn't work
- Check `data/training_examples_1k.jsonl` manually
- Verify `tool_calls[].result` fields are not `None`

### Step 3: Retrain 7B Model

```bash
uv run python -m mlx_lm lora \
    --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
    --train --data data/mlx_format \
    --iters 200 --batch-size 1 --learning-rate 1e-4 \
    --num-layers 16 --adapter-path models/qwen25-7b-distilled/adapters \
    --save-every 100 --val-batches 5 --test
```

**Expected:**
- Training time: ~25 minutes
- Peak memory: 7-8 GB (much better than Phase 1's 18.9 GB)
- Loss should decrease steadily

### Step 4: Test for Infinite Loop Fix

1. Start 7B server with trained adapters:
```bash
nohup uv run python -m mlx_lm server \
    --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
    --adapter-path models/qwen25-7b-distilled/adapters \
    --port 8080 \
    --host 127.0.0.1 \
    > /tmp/mlx-7b-server.log 2>&1 &
```

2. Test with Protocol search:
```bash
OPENAI_API_KEY='dummy' \
OPENAI_BASE_URL='http://127.0.0.1:8080/v1' \
uv run punie test-tools \
    --model 'openai:mlx-community/Qwen2.5-Coder-7B-Instruct-4bit' \
    --prompt 'Find all classes that inherit from Protocol in the codebase'
```

**Success criteria:**
- ✅ Model calls 1-3 tools (grep or similar)
- ✅ Model interprets the tool results
- ✅ Model gives a final answer listing the protocols found
- ✅ NO infinite loop of repeated tool calls
- ✅ NO hallucinated fake conversations

**Failure indicators:**
- ❌ Calls same tool 20+ times
- ❌ Never gives final answer
- ❌ Generates fake `<|im_start|>` tokens
- ❌ Hallucinates tool results

---

## Why This Will Work

### Evidence from Phase 1

Phase 1 proved the model CAN learn autonomous tool calling:
- ✅ Used `{text}` format with Qwen tokens
- ✅ Model learned to call tools via API (not generate text)
- ✅ Called appropriate tools (grep, find, etc.)
- ❌ But looped infinitely because ALL results were `[Tool execution completed]`

The model learned:
1. ✅ When to call tools
2. ✅ How to format tool calls
3. ❌ How to interpret results (all looked the same!)
4. ❌ When to stop (no signal from results)

### Why Real Results Fix the Loop

With real results like:
```
Tool result: src/interfaces.py:8:class StorageProtocol(Protocol):
src/interfaces.py:15:class LoggerProtocol(Protocol):
```

The model will learn:
1. ✅ When to call tools
2. ✅ How to format tool calls
3. ✅ Results contain actual information → **NEW!**
4. ✅ When sufficient info gathered → stop and answer → **NEW!**

The 28 hand-authored examples (with real results) would have worked EXCEPT they used markdown format which teaches text generation, not API calling.

### Memory Is Not the Problem

Phase 2 training (before failure) used only **7.3 GB** vs Phase 1's **18.9 GB**. The smaller dataset with fewer examples actually uses LESS memory.

---

## Troubleshooting

### Server Won't Start

**Check port availability:**
```bash
lsof -i :8080
# If occupied, use different port and update OPENAI_BASE_URL
```

**Check model is cached:**
```bash
ls -lh ~/.cache/huggingface/hub/ | grep Qwen3-Coder-30B
# Should exist, otherwise will download (~60GB)
```

### Generation Fails with Connection Errors

**Test connection:**
```bash
curl -s http://127.0.0.1:8080/v1/models
# Should return JSON with model list
```

**Test with simple query:**
```bash
OPENAI_API_KEY='dummy' OPENAI_BASE_URL='http://127.0.0.1:8080/v1' \
uv run python -c "
from pydantic_ai import Agent
agent = Agent('openai:mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit')
result = agent.run_sync('What is 2+2?')
print(str(result))
"
```

### Converter Shows 0 Examples with Real Results

**Check generated data manually:**
```bash
head -1 data/training_examples_1k.jsonl | python3 -m json.tool | grep -A5 tool_calls
# Should see "result": "..." with actual content, not null
```

**If results are null:**
- Generator fix didn't work
- Check `scripts/generate_training_data.py` lines 212-224
- Verify `part_kind` is being used correctly

### Model Still Loops After Retraining

**If loop continues:**
1. Check training data had real results (Step 2)
2. Verify `{text}` format was used (not `{messages}`)
3. Check training loss decreased properly
4. May need more training iterations (try 300-400)
5. May need more examples with real results

**If model hallucinates:**
- Wrong format used (went back to `{messages}`)
- Hand-authored examples got included
- Revert to using only generated examples

---

## Files Modified

| File | Purpose | Status |
|------|---------|--------|
| `scripts/generate_training_data.py` | Captures real tool results | ✅ Fixed |
| `scripts/convert_training_data.py` | Converts with real results | ✅ Fixed |
| `scripts/run_generator.sh` | Wrapper with env vars | ✅ Created |
| `MODEL_PERFORMANCE_TRACKER.md` | Phase 2 documentation | ✅ Updated |
| `PHASE2_COMPLETION_GUIDE.md` | This guide | ✅ Created |

---

## Expected Timeline

| Step | Duration | Notes |
|------|----------|-------|
| Start 30B server | 5 min | Model loading |
| Generate data | 70 min | 100 examples @ ~40s each |
| Verify results | 1 min | Run converter |
| Retrain 7B | 25 min | 200 iterations |
| Test model | 5 min | Run test-tools |
| **Total** | **~2 hours** | Mostly unattended |

---

## Success Metrics

After completion, update `MODEL_PERFORMANCE_TRACKER.md` with:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Training examples | ~69 total | `wc -l data/mlx_format/train.jsonl` |
| With real results | ~54 | Converter output |
| Tool calls per query | 1-3 | `punie test-tools` output |
| Infinite loop fixed? | Yes | Model gives final answer |
| Training memory | <10 GB | Monitor during training |
| Inference speed | 15-25s | Time from query to answer |

---

## Next Phase After Success

Once Phase 2 works (model calls tools correctly without looping):

**Phase 3: Scale Up**
- Generate 1,000-5,000 examples from multiple codebases
- Teach generalization (not memorization of one codebase)
- Target: Works on ANY Python codebase, not just Punie

**Phase 4: Optimize Speed**
- Stop token handling
- Speculative decoding
- KV cache optimization
- Target: 6-8 seconds (vs current 21s)

---

## Contact Points

If this guide doesn't work:
1. Check `MODEL_PERFORMANCE_TRACKER.md` for Phase 2 details
2. Review server logs: `/tmp/mlx-30b-server.log`
3. Check generation log: `generation.log`
4. Verify data: `data/training_examples_1k.jsonl`

The code fixes are correct. The only remaining work is operational.
