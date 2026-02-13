# Knowledge Distillation Workflow: 30B → 7B

**Complete end-to-end guide for training a 7B model with 30B-level autonomous reasoning**

---

## Overview

### Goal
Train a 7B model to autonomously use tools like 30B, but with:
- ✅ 3x faster (8s vs 25s)
- ✅ 2-3x less RAM (4-6GB vs 16GB)
- ✅ Same autonomous reasoning capability

### Approach
**Knowledge Distillation:** Use 30B as "teacher" to generate training data, fine-tune 7B with LoRA

### Timeline
- **Phase 1:** Generate training data (1-2 hours) ← Currently here
- **Phase 2:** Fine-tune 7B (6-8 hours overnight)
- **Phase 3:** Evaluate (30 minutes)
- **Total:** ~1 day end-to-end

---

## Phase 1: Generate Training Data ✅ IN PROGRESS

### Status
- **Script:** `scripts/generate_training_data.py`
- **Running:** Background task (ID: bfcb818)
- **Target:** 100 examples for MVP
- **Progress:** ~11/100 examples

### What It Does

```
Query template → 30B inference → Tool usage → Answer
                                      ↓
                    Save (query, tool_calls, answer)
```

### Language Scope
- ✅ Python (primary)
- ✅ JavaScript/TypeScript
- ✅ HTML
- ✅ CSS

### Query Categories (8 types)

1. **Code Search** - "Which classes subclass from Protocol?"
2. **Import Analysis** - "Find all files that import 'asyncio'"
3. **Function Discovery** - "What are parameters for create_pydantic_agent?"
4. **Counting** - "How many test files in tests/?"
5. **Pattern Search** - "List all dataclasses in src/punie/training/"
6. **Web Frontend** - "Find all button elements in templates/"
7. **Web Backend** - "What routes are defined in app.py?"
8. **Negative Examples** - "What is 25 × 4?" (no tools needed)

### Monitor Progress

```bash
# Check examples generated
wc -l data/training_examples_1k.jsonl

# View latest batch output
tail -f /private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-punie/tasks/bfcb818.output

# Inspect a sample
head -1 data/training_examples_1k.jsonl | python -m json.tool
```

### When Complete

**Validation checklist:**
- [ ] ≥80 examples generated (target: 100)
- [ ] >80% have tool calls (positive examples)
- [ ] ~20% no tool calls (negative examples)
- [ ] Diverse query categories
- [ ] No fatal errors

**If successful:** Proceed to Phase 2
**If <50 examples:** Investigate errors, re-run with adjustments

---

## Phase 2: Fine-Tune 7B with LoRA ⏳ NEXT

### When to Start
After Phase 1 completes with ≥80 valid examples

### Command

```bash
./scripts/train_lora.sh
```

### What It Does

1. **Validates** training data exists
2. **Configures** LoRA parameters:
   - Model: Qwen2.5-Coder-7B-Instruct-4bit
   - Batch size: 4
   - Learning rate: 1e-4
   - LoRA rank: 16
   - Epochs: 3

3. **Trains** adapter layers (~6-8 hours)
4. **Saves** to `models/qwen25-7b-distilled/adapters/`

### Resource Requirements

| Resource | Usage |
|----------|-------|
| RAM | 16-20GB peak |
| Disk | ~2GB for adapter |
| Time | 6-8 hours (overnight) |
| Power | ~$0.15 electricity |

### Monitor Training

```bash
# Training runs in foreground with progress bars
# Look for:
# - Loss decreasing each epoch
# - Validation accuracy improving
# - No OOM (out of memory) errors
```

### Success Criteria

- ✅ Training completes all epochs
- ✅ Loss decreases steadily
- ✅ Validation accuracy >70%
- ✅ Adapter files saved

---

## Phase 3: Evaluate Distilled Model ⏳ PENDING

### When to Start
After Phase 2 completes successfully

### Prerequisites

1. **Load 7B + adapter to server:**
   ```bash
   # Example with mlx_lm (adjust for your setup)
   python -m mlx_lm server \
     --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
     --adapter-path models/qwen25-7b-distilled/adapters \
     --port 8081
   ```

2. **Ensure 30B server still running** (for comparison)

### Command

```bash
uv run python scripts/evaluate_distilled_model.py
```

### What It Does

Runs 5 benchmark tasks on both models:
1. Protocol search
2. Import usage
3. Function signature
4. Test count
5. Dataclass search

Compares:
- Success rate
- Autonomous tool usage
- Accuracy
- Speed

### Success Criteria

| Metric | Target | Why |
|--------|--------|-----|
| Autonomous tool usage | **>80%** | Core capability |
| Accuracy | >75% | Quality threshold |
| Success rate | >60% | Overall performance |

### Possible Outcomes

#### 🎉 Success (>80% autonomous)
- 7B learned autonomous reasoning!
- Deploy to production
- 3x faster, 2-3x less RAM

#### ⚠️ Partial (60-80% autonomous)
- Shows promise, needs more data
- Options:
  - Generate 1K examples (not 100)
  - Train 5 epochs (not 3)
  - Accept for some use cases

#### ❌ Failure (<60% autonomous)
- 7B lacks capacity for reasoning
- Options:
  - Try 14B model (if available)
  - Stick with 30B + optimizations
  - Hybrid: 7B + 30B delegation

---

## Decision Tree

```
Data Generation Complete?
├─ Yes, ≥80 examples
│  └─> Start Phase 2 (training)
└─ No, <80 examples
   └─> Fix issues, re-run

Training Complete?
├─ Yes, loss decreased
│  └─> Start Phase 3 (evaluation)
└─ No, errors/OOM
   └─> Reduce batch size, retry

Evaluation Result?
├─ >80% autonomous
│  └─> 🎉 Deploy to production!
├─ 60-80% autonomous
│  └─> Generate more data, retrain
└─ <60% autonomous
   └─> Try 14B or stick with 30B
```

---

## Files & Directories

### Scripts (ready to run)
- ✅ `scripts/generate_training_data.py` - Phase 1
- ✅ `scripts/train_lora.sh` - Phase 2
- ✅ `scripts/evaluate_distilled_model.py` - Phase 3

### Data (generated)
- 🔄 `data/training_examples_1k.jsonl` - Training data (in progress)
- ⏳ `models/qwen25-7b-distilled/adapters/` - LoRA weights (pending)
- ⏳ `evaluation_results.json` - Benchmark results (pending)

### Documentation
- ✅ `KNOWLEDGE_DISTILLATION_PLAN.md` - Strategic overview
- ✅ `DATA_GENERATION_STATUS.md` - Phase 1 details
- ✅ `DISTILLATION_WORKFLOW.md` - This file (complete workflow)

---

## Quick Reference

### Current Status
- [x] 30B validated (80% success, 25s avg)
- [x] 7B tested (fast but no autonomous reasoning)
- [x] Scope defined (Python + HTML/CSS/JS)
- [x] Data generation scripts created
- [ ] Training data generated (11/100 in progress)
- [ ] LoRA training
- [ ] Evaluation

### Next Action
**Wait for data generation to complete** (~30-45 min remaining)

Then:
```bash
# Validate data
wc -l data/training_examples_1k.jsonl

# Start training (overnight)
./scripts/train_lora.sh

# Evaluate (tomorrow morning)
uv run python scripts/evaluate_distilled_model.py
```

---

## Troubleshooting

### Data Generation Slow
- **Normal:** 30-60s per query
- **Too slow (>2min/query):** Reduce batch size from 5 to 3

### Training OOM
- Reduce `BATCH_SIZE` from 4 to 2 in `train_lora.sh`
- Close other apps to free RAM

### Evaluation Server Issues
- Ensure 7B + adapter loaded to port 8081
- Ensure 30B still running on port 8080

---

**Ready to complete the knowledge distillation pipeline!** 🚀
