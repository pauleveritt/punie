# Knowledge Distillation: Data Generation In Progress 🚀

**Started:** 2026-02-12
**Status:** Running in background (Task ID: bfcb818)
**Goal:** Generate 100 training examples for MVP

---

## What's Happening Now

The 30B model is generating training data by:

1. **Query Generation:** Created 100+ diverse queries from templates
2. **30B Inference:** Running each query through 30B model
3. **Data Capture:** Recording query → tool_calls → answer
4. **Batch Processing:** 5 concurrent queries at a time

### Query Categories

- **Code Search:** "Which classes subclass from Protocol?"
- **Import Analysis:** "Find all files that import 'asyncio'"
- **Function Discovery:** "What are the parameters for create_pydantic_agent?"
- **Counting:** "How many test files in tests/?"
- **Pattern Search:** "List all dataclasses in src/punie/training/"
- **Negative Examples:** "What is 25 × 4?" (no tools needed)

---

## Expected Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Query generation | ~1 min | ✅ Done |
| Batch 1-20 (100 queries) | ~30-60 min | 🔄 Running |
| Validation | ~5 min | ⏳ Pending |
| **Total** | **~45-75 min** | **In Progress** |

**Estimated completion:** ~1 hour from start

---

## Output Files

**Training data:**
- `data/training_examples_1k.jsonl` - JSONL format
- One example per line
- Checkpointed after each batch (safe to interrupt)

**Example format:**
```json
{
  "query": "Which classes in this codebase subclass from Protocol?",
  "reasoning": "Need to search/analyze codebase using 2 tool(s)",
  "tool_calls": [
    {"tool": "run_command", "args": {"command": "grep", ...}},
    {"tool": "read_file", "args": {"path": "src/punie/http/types.py"}}
  ],
  "answer": "Based on my search, I found 6 Protocol classes...",
  "metadata": {
    "category": "code_search",
    "execution_time": 30.83,
    "tool_count": 2,
    "model": "qwen3-30b-a3b-instruct-2507-mlx"
  }
}
```

---

## What Happens After

### 1. Validate Training Data (~5 min)
- Check tool usage distribution
- Verify answer quality
- Balance positive/negative examples

### 2. Prepare for LoRA Training (~10 min)
- Convert JSONL to MLX format
- Split train/validation sets (90/10)
- Set up training config

### 3. Fine-Tune 7B Overnight (~6-8 hours)
```bash
mlx_lm.lora \
  --model Qwen2.5-Coder-7B-Instruct \
  --train \
  --data data/training_examples_1k.jsonl \
  --iters 300 \
  --batch-size 4
```

### 4. Evaluate Distilled 7B (next day)
- Run same 5-task benchmark
- Compare to 30B baseline
- **Success = >80% autonomous tool usage**

---

## Success Criteria

### MVP (100 examples)

| Metric | Target | Why |
|--------|--------|-----|
| Tool usage rate | >80% | Most queries should use tools |
| Negative examples | ~20% | Balance: when NOT to use tools |
| Diverse categories | 5+ | Cover all query types |
| Valid responses | >95% | 30B should answer correctly |

### Quality Indicators

✅ **Good:** 80+ examples with tool calls, 20 without
✅ **Good:** Even distribution across categories
✅ **Good:** Execution time 15-40s per query
⚠️ **Warning:** >50% failed queries → server issues
❌ **Bad:** <50% tool usage → need better queries

---

## Monitoring Progress

**Check status:**
```bash
# View latest output
cat /private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-punie/tasks/bfcb818.output

# Check data file
wc -l data/training_examples_1k.jsonl

# View sample
head -1 data/training_examples_1k.jsonl | python -m json.tool
```

**Expected output:**
```
Batch 1/20 (5 queries)...
  ✅ 5 succeeded
  Progress: 5/100 examples

Batch 2/20 (5 queries)...
  ✅ 4 succeeded
  Progress: 9/100 examples

...
```

---

## Next Steps (When Complete)

### If Generation Succeeds (>80 examples)

1. ✅ Review dataset quality
2. ✅ Prepare MLX training format
3. ✅ Launch overnight LoRA training
4. ✅ Evaluate tomorrow morning

### If Generation Has Issues

**<50 examples:** Increase timeout, reduce batch size
**Low tool usage:** Add more codebase-specific queries
**Many failures:** Check server health, reduce concurrency

---

## Estimated Costs

| Resource | Usage | Cost |
|----------|-------|------|
| 30B inference | 100 queries × 30s | ~50 min compute |
| M1 power | 1 hour | ~$0.02 electricity |
| Storage | ~5 MB JSONL | Free |
| **Total** | **~1 hour** | **~$0.02** |

---

## Files Created

- ✅ `scripts/generate_training_data.py` - Data generation pipeline
- 🔄 `data/training_examples_1k.jsonl` - Training data (in progress)
- ⏳ `scripts/train_lora.sh` - Training script (next)
- ⏳ `scripts/evaluate_distilled_model.py` - Evaluation (next)

---

**Status:** Data generation running smoothly! 🚀
**Next Update:** When generation completes (~45-75 min)
