# Knowledge Distillation Plan: 30B → 7B

**Goal:** Train a 7B model to have 30B-level autonomous reasoning
**Platform:** M1 Mac, 32GB RAM
**Cost:** ~$20 (electricity)
**Timeline:** 1-2 weeks

---

## Why This Approach?

### The Problem
- **1.5B & 7B models:** Fast but no autonomous reasoning (hallucinate)
- **30B model:** Autonomous reasoning ✅ but too slow (93s) and heavy (16GB RAM)
- **Need:** 7B speed + 30B reasoning capability

### The Solution: Knowledge Distillation
Use 30B to generate training data, then teach 7B to mimic its reasoning patterns.

---

## Three-Phase Plan

### Phase 1: Generate Training Data (1-2 days)

**Use 30B as "teacher" to create synthetic examples:**

```python
# Example training data point:
{
    "query": "What classes in this codebase implement a protocol?",
    "reasoning": "I need to search the codebase for Protocol classes",
    "tool_calls": [
        {"tool": "run_command", "args": ["grep", ["-r", "class.*Protocol", "."]]},
        {"tool": "read_file", "args": ["src/punie/http/types.py"]}
    ],
    "answer": "Found 6 Protocol classes: HttpAppFactory, Client, ..."
}
```

**Dataset Requirements:**

| Category | Examples | Purpose |
|----------|----------|---------|
| Code search | 2,000 | Protocol search, import finding, dataclass search |
| Code analysis | 2,000 | Function signatures, parameter analysis, complexity |
| Multi-step reasoning | 2,000 | Chained tool usage, file discovery then reading |
| Negative examples | 1,000 | Math, general knowledge (NO tools needed) |
| Edge cases | 1,000 | Ambiguous queries, error handling |
| **Total** | **8,000-10,000** | Diverse coverage of codebase exploration |

**Generation Strategy:**

1. **Create query templates:**
   ```python
   templates = [
       "What classes subclass from {base_class}?",
       "Find all files that import '{module}'",
       "What are the parameters for {function}?",
       "How many {pattern} are in {directory}?",
   ]
   ```

2. **Generate variants:**
   - Substitute real values from codebase
   - Run 30B on each query
   - Save query + tool_calls + response

3. **Parallelization:**
   - Run 10-20 queries simultaneously
   - Queue overnight jobs
   - 30B at 93s/query × 10K = ~10 days sequential
   - **Optimized:** 2-3 days with parallelization

**Data Quality Checks:**
- ✅ 30B used tools for search queries
- ✅ 30B didn't use tools for math/general knowledge
- ✅ Responses are accurate (validate against expected results)
- ✅ Diverse tool usage (grep, read_file, list_files)

---

### Phase 2: Fine-tune 7B with LoRA (2-5 days)

**Technique:** QLoRA (Quantized Low-Rank Adaptation)

**Why LoRA?**
- Only trains small adapter layers (~100-200MB)
- Keeps base 7B model frozen
- 10-100x faster than full fine-tuning
- Fits in 32GB RAM comfortably

**MLX-LM LoRA Training:**

```bash
# Convert data to MLX format
mlx_lm.convert --hf-path Qwen2.5-Coder-7B-Instruct

# Train LoRA adapter
mlx_lm.lora \
  --model Qwen2.5-Coder-7B-Instruct \
  --train \
  --data training_data.jsonl \
  --iters 1000 \
  --batch-size 4 \
  --lora-layers 16 \
  --adapter-path ./lora_adapters
```

**Training Configuration:**

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| Batch size | 4 | Fits in 32GB with 7B model |
| Learning rate | 1e-4 | Standard for LoRA |
| LoRA rank | 8-16 | Balance between capacity and efficiency |
| Epochs | 3-5 | Avoid overfitting |
| Iterations | 1000-3000 | ~10K examples ÷ batch 4 × epochs |

**Resource Requirements:**

| Resource | Usage | Notes |
|----------|-------|-------|
| RAM | 16-20GB | 7B in 4-bit + gradients |
| Disk | 50GB | Model + data + checkpoints |
| Time | 18-30 hours | ~6 hours/epoch × 3-5 epochs |
| Power | ~$15-20 | Running M1 24/7 for 2-3 days |

**Training Schedule:**
- Evening: Start training
- Overnight: Runs unattended
- Morning: Check progress, adjust hyperparameters
- Repeat for 2-3 nights

---

### Phase 3: Evaluate & Iterate (ongoing)

**Evaluation Suite:** Use existing `eval_autonomous_tool_usage.py`

**Success Criteria:**

| Metric | Target | Current 7B | Current 30B |
|--------|--------|------------|-------------|
| Autonomous tool usage | >80% | 0% ❌ | 100% ✅ |
| Accuracy | >90% | 0% ❌ | 100% ✅ |
| Speed | <20s | 8s ✅ | 93s ❌ |
| RAM | <8GB | 4-6GB ✅ | 16GB ❌ |

**Iteration Strategy:**

1. **First iteration (baseline):**
   - Train on 1K examples (quick test)
   - Evaluate on Protocol search + 4 tasks
   - If >50% → promising, scale up
   - If <50% → distillation won't work

2. **Second iteration (scale up):**
   - Train on full 10K examples
   - Evaluate on full 12-task autonomous suite
   - If >80% → production ready!
   - If 50-80% → need more data or different approach

3. **Third iteration (optimize):**
   - Analyze failure cases
   - Generate targeted examples for weak areas
   - Retrain with augmented dataset
   - Target: >90% autonomous reasoning

---

## Minimal Viable Experiment (Week 1)

**Goal:** Validate distillation works before investing weeks

### Day 1-2: Generate 1K High-Quality Examples
- Focus on most common queries (Protocol search, imports, functions)
- Include clear positive and negative examples
- Validate 30B responses are perfect

### Day 3: Train Overnight
- LoRA fine-tune on 1K examples
- ~6 hours training time

### Day 4: Evaluate
- Run on 5 real tasks
- Measure autonomous tool usage rate
- **Decision point:**
  - >80% success → Scale to 10K examples
  - 50-80% success → Need more examples or better data
  - <50% success → Distillation insufficient, try 14B model

### Day 5-7: Iterate or Pivot
- If promising → generate more data, retrain
- If not → document findings, try alternative approach

---

## Alternative Approaches (If Distillation Fails)

### Plan B: Try 14B Model
- `Qwen2.5-Coder-14B-Instruct-4bit` (if exists)
- Might have autonomous reasoning naturally
- ~8-10GB RAM, faster than 30B

### Plan C: Hybrid System
- Use 7B for simple queries (cached patterns)
- Delegate complex queries to 30B
- Best of both worlds: fast + autonomous

### Plan D: Accept 30B with Optimizations
- Reduce KV cache (`max_kv_size=2048`)
- Response caching for common queries
- Selective loading (lazy-load 30B only when needed)

---

## Tools & Scripts Needed

### 1. Data Generation Pipeline
```python
# scripts/generate_training_data.py
- Query template engine
- 30B inference runner
- Response validator
- JSONL formatter
```

### 2. Training Pipeline
```bash
# scripts/train_lora.sh
- MLX-LM LoRA training
- Checkpoint saving
- Hyperparameter tuning
```

### 3. Evaluation Pipeline
```python
# scripts/evaluate_distilled_model.py
- Load 7B + LoRA adapter
- Run autonomous tool usage eval
- Compare to 30B baseline
```

---

## Success Probability Assessment

### Factors Favoring Success ✅
- 30B proves autonomous reasoning is learnable
- 7B has base language understanding (just lacks tool reasoning)
- LoRA is proven for task-specific fine-tuning
- Narrow domain (codebase exploration, not general coding)

### Risks ❌
- Autonomous reasoning might require model capacity (not just training)
- 7B might lack "reasoning neurons" that 30B has
- Dataset might need 50K+ examples, not 10K
- Overfitting to training patterns without generalizing

### Probability Estimate
- **60-70% chance** of achieving >80% autonomous tool usage
- **30-40% chance** of complete success (>90%)
- **Worth trying** given low cost ($20 + 1-2 weeks)

---

## Next Steps

1. ✅ Document plan (this file)
2. 🔲 Validate 30B on full 5-task suite (establish baseline)
3. 🔲 Compare Qwen2.5-32B vs Qwen3-30B (find best teacher)
4. 🔲 Create data generation scripts
5. 🔲 Run minimal viable experiment (1K examples)
6. 🔲 Evaluate and decide: scale up or pivot

---

## Files to Create

- `scripts/generate_training_data.py` - Data generation pipeline
- `scripts/train_lora.sh` - Training script
- `scripts/evaluate_distilled_model.py` - Evaluation harness
- `data/training_queries.jsonl` - Query templates
- `data/training_examples.jsonl` - Generated training data
- `models/lora_adapters/` - Trained adapter weights

---

**Status:** Plan documented, ready to begin Phase 0 (validation experiments)
**Date:** 2026-02-12
**Next:** Run Option A (validate 30B) + Option B (compare models)
