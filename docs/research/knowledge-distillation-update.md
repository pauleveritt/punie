# Knowledge Distillation Realistic Update

**Date:** February 13, 2026
**Based on:** Complete 30B→7B distillation experiment

## What We Learned

### Original Plan vs Reality

**Original assumptions:**
- Small dataset (100 examples) would be sufficient
- 7B model could learn autonomous tool use
- Knowledge distillation would work with simple Q&A format
- Training time: 6-8 hours
- Expected performance: 8-12s inference

**Actual results:**
- Generated 69 examples (limited by time/quality)
- 7B learned to MEMORIZE answers, not use tools
- Needs explicit tool execution traces, not Q&A
- Training time: 11 minutes (much faster!)
- Actual performance: 21s inference (slower than estimated)

---

## Critical Discovery: Memorization vs Generalization

**The Core Problem:**
The 7B distilled model answered the protocols query correctly (100% accuracy) but did NOT use tools autonomously. It memorized the answer from training data instead of learning HOW to search.

**Evidence:**
- Response said "I've analyzed the codebase..."
- But didn't actually call grep or read_file tools
- Listed all 7 Protocol classes correctly
- This only works for queries about THIS codebase

**Why this happened:**
1. **Dataset too small:** 69 examples from ONE codebase
2. **No tool execution traces:** Training showed Query→Answer, not Query→Tools→Results→Answer
3. **Model capacity:** 7B may be too small for general reasoning

---

## Root Cause Analysis: The Training Data Pipeline Bug

**Date:** February 13, 2026

**Smoking gun found:** `scripts/convert_training_data.py` strips ALL tool-calling information from training data.

**What happened:**
1. `generate_training_data.py` correctly generates rich examples with:
   - `query`: "Which classes inherit from Protocol?"
   - `reasoning`: "Need to search/analyze codebase"
   - `tool_calls`: [{"tool": "run_command", "args": {...}}]
   - `answer`: "Found 7 Protocol classes..."

2. `convert_training_data.py` then STRIPS all of this down to:
   ```
   User: {query}
   Assistant: {answer}
   ```

**Result:** The model learned "query X → answer Y" mappings (memorization) instead of "query X → use tools → analyze results → synthesize answer" (reasoning).

**Why the model didn't learn tool usage:**
- Training data never showed tool calls
- Training data never showed tool results
- Training data never showed multi-turn reasoning
- Model had no examples of HOW to use tools, only WHAT the final answers were

**The fix:** Preserve multi-turn conversations in training data:
```
User: {query}
Assistant: <tool_call>...</tool_call>
User: Tool result: {result}
Assistant: {analysis}
```

This is why the 30B baseline works but the 7B distilled model doesn't—we accidentally removed the most important part of the training data!

---

## Realistic Path Forward

### Quick Wins (Implement First)

**1. Fix Stop Token Issue** (5-10s speedup)
```bash
# Current: Generates repeated <|im_end|>!!! garbage
# Fix: Better stop sequences
--stop "<|im_end|>"
--max-tokens 200
```
**Expected:** 21s → 15s (30% faster)
**Effort:** Low (config change)
**Risk:** None

**2. Response Format Training** (5-10s speedup)
```python
# Train for concise responses, not conversational
# Remove: "Would you like me to..." "Let me help..." etc.
# Keep: Just the answer
```
**Expected:** 15s → 10s (30% faster)
**Effort:** Medium (retrain with better format)
**Risk:** Low

**3. Speculative Decoding** (2-3x speedup)
```bash
mlx_lm.server \
  --model Qwen2.5-Coder-7B-Instruct-4bit \
  --draft-model Qwen2.5-Coder-1.5B-Instruct-4bit \
  --adapter-path adapters/
```
**Expected:** 10s → 4-5s (2x faster)
**Effort:** Medium (need 1.5B model)
**Risk:** Medium (quality may vary)

**Combined estimate:** 21s → 4-6s (4-5x faster)

---

### Proper Tool Use Training (The Hard Part)

**Problem:** Current approach learns WHAT the answer is, not HOW to find it.

**Solution:** Train on tool execution traces

**Two approaches:**

#### Approach A: Ethical Dataset Collection
1. **Use existing tool-calling datasets:**
   - Gorilla API dataset (Apache 2.0)
   - ToolBench (filtered for Python)
   - Berkeley Function Calling Leaderboard data
   - **Benefit:** Legally clear, diverse examples
   - **Challenge:** May not match Punie's tool format exactly

2. **Generate synthetic traces:**
   - Use 30B to actually CALL tools (not just answer)
   - Capture: Query → run_command(grep...) → Results → Answer
   - Store full conversation with tool calls
   - **Benefit:** Perfect format match
   - **Challenge:** Expensive (30B is slow)

3. **Hand-author critical examples:**
   - Create 50-100 high-quality tool-calling examples
   - Cover common patterns (search, read, analyze)
   - Supplement with synthetic/downloaded data
   - **Benefit:** High quality, perfect format
   - **Challenge:** Time-consuming

**Recommendation:** Hybrid approach
- Hand-author 50 critical examples (1-2 days)
- Generate 200 synthetic traces from 30B (overnight)
- Download 500 from ethical datasets (filtered for relevance)
- **Total:** 750 examples with actual tool execution

#### Approach B: Larger Model
- Try 14B or 20B base model
- May have inherent reasoning capacity 7B lacks
- Trade-off: Slower inference, more memory
- **Consider if:** A fails to improve tool usage

---

### Updated Training Requirements

**Minimum for autonomous tool use:**
- Examples: 500-1,000 (not 69)
- Diversity: 10+ different codebases (not 1)
- Format: Full tool execution traces (not Q&A)
- Training: Tool call prediction as explicit target
- Validation: Test on UNSEEN codebases

**Estimated effort:**
- Data generation: 3-5 days
- Training: 1-2 hours (fast part!)
- Evaluation: 1 day
- **Total:** ~1 week for proper attempt

---

## Recommended Next Steps

### Phase 1: Easy Wins (This Week)

**Priority 1: Stop token fix** (30 minutes)
1. Update server launch with `--stop "<|im_end|>"` and `--max-tokens 200`
2. Test on protocols query
3. Measure speedup
4. Commit if successful

**Priority 2: Speculative decoding test** (2 hours)
1. Download 1.5B draft model
2. Test speculative decoding with existing adapter
3. Measure speedup vs quality trade-off
4. Document findings

**Expected outcome:** 21s → 6-8s (2-3x faster) with minimal effort

### Phase 2: Proper Tool Training (Next Week)

**Option A: Start with ethical data** (Recommended)
1. Download Gorilla/ToolBench datasets (1 day)
2. Filter for Python + codebase tasks (1 day)
3. Hand-author 50 Punie-specific examples (2 days)
4. Train on combined dataset (1 hour)
5. Evaluate on new codebases (1 day)

**Option B: Generate synthetic traces** (Alternative)
1. Update data generation to capture tool calls (1 day)
2. Run 30B on 200 diverse queries (overnight)
3. Validate trace quality (1 day)
4. Train + evaluate (1 day)

**Decision point:** After Phase 1 easy wins, choose A or B based on:
- Legal comfort with datasets
- Time available for hand-authoring
- 30B server stability

### Phase 3: Production Optimization (Future)

Only after Phase 2 shows autonomous tool use:
1. KV cache optimization
2. 3-bit quantization testing
3. Hybrid architecture (fast router + LLM)
4. Continuous training pipeline

---

## Success Metrics

### Phase 1 (Easy Wins)
- ✅ Inference time: <10s (currently 21s)
- ✅ No quality regression
- ✅ Stop token garbage removed

### Phase 2 (Proper Tool Training)
- ✅ Autonomous tool usage: >80% on NEW codebases
- ✅ Accuracy: >75% (currently 100% on memorized data)
- ✅ Generalizes beyond training data
- ⚠️ Speed: May be slower initially, optimize in Phase 3

### Phase 3 (Production)
- ✅ Inference: 4-6s
- ✅ Autonomous: >80%
- ✅ Memory: <8GB
- ✅ Generalizes to any codebase

---

## Key Takeaways

1. **Infrastructure works:** Training pipeline is solid (11 min, 95%+ loss reduction)
2. **Data quality matters more than quantity:** 69 examples of wrong format < 100 examples of right format
3. **7B can learn patterns:** Just not complex reasoning with tiny datasets
4. **Quick wins available:** 2-3x speedup with config changes
5. **Real work is data curation:** Getting proper tool execution traces is the challenge

**Bottom line:** We have a working training pipeline. Now we need better training data that shows HOW to use tools, not just WHAT the answers are.
