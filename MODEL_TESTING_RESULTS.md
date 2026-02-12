# Model Testing Results: Path to Production-Ready Agent

**Date:** February 12, 2026
**Goal:** Find a small, Python-focused model that autonomously uses tools

---

## Phase 1 Test Results

### Test 1: 1.5B with Explicit Instructions ❌

**Setup:**
- Model: Qwen2.5-Coder-1.5B-Instruct-4bit
- Prompt: "Search the codebase to find which classes subclass from Protocol. **Use the run_command tool with grep** to search..."

**Results:**
- Time: 17.52s
- Tool calls: **0**
- Behavior: Got stuck in infinite repetition loop
- Output: Explained HOW to use grep but didn't actually call the tool

**Key Finding:**
Even with explicit instructions, 1.5B **cannot bridge instruction to execution**. It understands the concept but lacks reasoning to perform the action.

---

### Test 2: 30B Autonomous Usage ✅ (Partial)

**Setup:**
- Model: Qwen3-Coder-30B-A3B-Instruct-4bit
- Prompt: "Which classes in this codebase subclass from Protocol?" (NO instructions)

**Results:**
- Time: ~8s (warm)
- Tool calls: **1** (run_command with grep)
- Behavior: Autonomously decided to search codebase
- Error: Wrong command format (passed full shell string instead of split args)

**Key Finding:**
30B **DOES have autonomous tool usage reasoning**! It:
- ✅ Decided to search without being told
- ✅ Chose appropriate tool (run_command + grep)
- ✅ Constructed reasonable grep pattern
- ❌ Used wrong tool signature format

**Command attempted:**
```bash
grep -r "class.*Protocol" . --include "*.py"
```

This is a **tool signature issue**, not a reasoning issue!

---

## Comparison Matrix

| Capability | 1.5B | 30B | Requirement |
|------------|------|-----|-------------|
| **Autonomous tool decision** | ❌ No | ✅ Yes | Critical |
| **Tool execution** | ❌ Explains only | ✅ Attempts | Critical |
| **Correct tool format** | N/A | ❌ Wrong | Fixable |
| **Speed (warm)** | 0.33s | ~8s | Nice-to-have |
| **Size** | 839 MB | 16 GB | Practical concern |
| **Eval score** | 92.9% | 75.0% | Misleading metric |

---

## Critical Insight: Eval Metrics Don't Predict Real Performance

**Why 1.5B scored 92.9% but fails real tasks:**

1. **Eval prompts likely simpler** - "Use read_file to..." vs "What's in the code?"
2. **Explicit tool instructions** in eval prompts
3. **Doesn't test autonomous decision-making**
4. **Missing metric:** "Does model know WHEN to use tools?"

**We need new eval categories:**
- Autonomous tool selection (not just execution)
- Multi-step reasoning with tools
- Real codebase exploration tasks

---

## Path Forward: Three Options

### Option A: Fix 30B Tool Signature Issue (RECOMMENDED)

**Problem:** 30B constructs commands incorrectly
- Passes: `run_command('grep -r "pattern" .')`
- Expected: `run_command('grep', ['-r', 'pattern', '.'])`

**Solutions:**

1. **Update tool to accept full command strings**
   ```python
   # In toolset.py
   async def run_command(command: str, ...):
       # Split command string into args
       import shlex
       cmd_parts = shlex.split(command)
       # Execute with split args
   ```

2. **Fine-tune 30B on correct tool signatures**
   - Training data with properly formatted tool calls
   - Focus on tool signature correctness
   - Conservative training (prevent catastrophic forgetting)

3. **Few-shot examples in prompt**
   - Show correct tool usage in system prompt
   - "Example: run_command('ls', ['-la'])"

**Recommendation: Try Solution #1 first** (code change, not training)

---

### Option B: Find 7B-14B "Sweet Spot" Model

**Hypothesis:** Autonomous reasoning emerges between 1.5B and 30B

**Test plan:**
1. Download Qwen2.5-Coder-7B-Instruct-4bit (~3.5 GB)
2. Test autonomous tool usage on Protocol search
3. If successful: We found the sweet spot!
4. If not: Try 14B

**Trade-offs:**
- 7B: Smaller/faster than 30B, but needs testing
- 14B: Middle ground, ~8 GB

---

### Option C: Specialized Agent Models

**Look for models trained for agentic behavior:**

Candidates to test:
1. **Hermes-2-Pro-Mistral-7B** (Nous Research)
   - Explicitly trained for function calling
   - ~7B parameters

2. **Functionary models**
   - Built specifically for tool use
   - Multiple sizes available

3. **WizardCoder-Python-7B-V1.0**
   - Python-focused
   - Check if MLX-quantized version exists

**Research needed:** Check if MLX 4-bit versions available

---

## Language Pruning Analysis

**Question:** Can we strip out non-English to get a smaller model without losing quality?

### The Problem

**Modern LLMs are multilingual by design:**
- Vocabulary includes tokens for 50+ languages
- Embedding layers contain multilingual representations
- Attention patterns learned across languages

**What "stripping non-English" would require:**

1. **Vocabulary pruning**
   - Remove Chinese, Korean, Arabic, etc. tokens
   - Reduces vocab from ~150K to ~50K tokens
   - Saves: ~100K * embedding_dim * 2 bytes

2. **Embedding matrix reduction**
   - For 1.5B model with 2048 embedding dim
   - Savings: ~100K tokens * 2048 * 2 bytes = **400 MB**

3. **Re-training required!**
   - Can't just delete tokens - breaks model
   - Need to retrain from pruned vocabulary
   - Requires full training run (expensive)

### My Opinion: NOT WORTH IT

**Why language pruning is a bad idea:**

#### 1. Marginal Size Savings
- **1.5B model:** 839 MB total
- **Vocab pruning saves:** ~400 MB
- **New size:** ~440 MB (52% original)
- **But:** Requires full retraining (expensive)

#### 2. More Efficient Alternatives

**Better ways to get smaller models:**

**Option A: Use existing smaller quantization**
- Try 3-bit instead of 4-bit
- Saves 25% with zero retraining
- May sacrifice some accuracy

**Option B: Knowledge distillation**
- Train 1.5B to mimic 30B behavior
- Preserve autonomous reasoning
- More effective than language pruning

**Option C: Just use larger model selectively**
- Use 30B only for complex tasks
- Cache in RAM, lazy-load
- 16 GB fits in 32 GB RAM

#### 3. Hidden Costs of Language Pruning

**You lose:**
- Code comments in other languages
- Variable names with non-ASCII characters
- International Python libraries (Chinese ML frameworks, etc.)
- Ability to read multilingual documentation
- Transfer learning benefits (multilingual pretraining helps English!)

**Example issues:**
```python
# This would break:
result = requests.get("https://api.example.com/用户/信息")  # Chinese
nombre = "usuario"  # Spanish variable
```

#### 4. The Real Problem Isn't Size

**Our actual problems:**
1. ❌ **1.5B lacks autonomous reasoning** (not fixable by pruning)
2. ❌ **Eval metrics don't predict real performance** (need better evals)
3. ❌ **30B has tool signature issues** (fixable with code)

**Language isn't the bottleneck!**

#### 5. Research Evidence

**Studies show:**
- Multilingual pretraining **improves** English performance
- "Curse of multilinguality" mainly affects very large vocabs (>250K)
- Language-specific pruning gives minimal gains vs distillation

### Recommendation: DON'T PRUNE LANGUAGES

**Instead, pursue:**

1. **Fix 30B tool signatures** (Option A above)
   - Immediate impact
   - No training required
   - Leverages existing working model

2. **Test 7B model** (Option B above)
   - Find sweet spot between size and reasoning
   - Faster than 30B, smarter than 1.5B

3. **Better evaluation metrics**
   - Test autonomous tool usage
   - Real-world codebase tasks
   - Measure what matters

4. **If size is critical:**
   - Try 3-bit quantization (easy)
   - Knowledge distillation (hard but worth it)
   - Selective loading (lazy load 30B)

---

## Revised Recommendation

**SHORT TERM (This Week):**

1. ✅ Fix 30B tool signature handling
   - Update `run_command` to accept full command strings
   - Test on Protocol search
   - If works → We have a solution!

2. ✅ Create better eval suite
   - Test autonomous tool usage
   - Real codebase exploration tasks
   - Use these metrics for future model selection

**MEDIUM TERM (Next 2 Weeks):**

3. Test Qwen2.5-Coder-7B-Instruct-4bit
   - Check autonomous reasoning
   - Measure tool usage correctness
   - Compare with 30B

4. If 7B works → Production model!
   - ~3.5 GB (fits easily in RAM)
   - Autonomous tool usage
   - Good speed/quality balance

**LONG TERM (If Needed):**

5. Consider knowledge distillation
   - Teach 1.5B to mimic 30B reasoning
   - Much more effective than language pruning
   - Preserves multilingual capability

---

## Key Takeaway

**The problem is reasoning capability, not language.**

- ❌ 1.5B can't reason about when to use tools
- ✅ 30B can reason but has fixable implementation issues
- ❌ Language pruning won't fix reasoning gaps
- ✅ Larger models or better architectures will

**Next step: Fix 30B tool signatures and see if we have a production-ready model.**
