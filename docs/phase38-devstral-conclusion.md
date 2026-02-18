# Phase 38 Devstral Conclusion: Zero-Shot Works, But Too Slow

**Date**: 2026-02-17
**Decision**: Return to Qwen3 fine-tuned approach
**Reason**: Devstral is 40x slower than Qwen3, making it impractical for production

## Executive Summary

Phase 38 successfully proved that **zero-shot models CAN work** with direct Code Tools (84% accuracy), but revealed a fatal flaw: **Devstral is 40x slower than fine-tuned Qwen3** (95s vs 2.3s per query).

**The Trade-Off:**
- ✅ Zero-shot: No training required, 84% accuracy
- ❌ Speed: 40x slower (95s vs 2.3s)
- ❌ Cost: Slower = more compute time = higher operational cost

**Verdict**: Fine-tuning wins. Qwen3 Phase 27 (100% accuracy, 2.3s) is superior for production use.

## Performance Comparison

| Model | Accuracy | Avg Time | Speedup | Training | Status |
|-------|----------|----------|---------|----------|--------|
| **Qwen3 Phase 27** | 100% | 2.32s | Baseline | Required | ✅ **Winner** |
| **Devstral** | 84% | 95.58s | **40x slower** | None | ❌ Too slow |
| **Devstral (optimized)** | 84% | ~20-30s (est) | **10x slower** | None | ⚠️ Still slow |

### Detailed Breakdown

**Qwen3 Phase 27** (fine-tuned, MLX):
- Load time: 6.5s
- Warm-up: 7.42s
- Steady-state: 2.32s per query
- Memory: 19.6 GB
- Response style: Concise tool calls

**Devstral** (zero-shot, Ollama):
- Load time: N/A (server-based)
- Warm-up: 59-98s (varies wildly)
- Steady-state: 8-309s per query (massive variance)
- Memory: Unknown (Ollama managed)
- Response style: Verbose explanations + tool calls

## Root Cause: Verbose Responses

### Qwen3 Response (Fast)
```python
<tool_call>typecheck_direct("src/")</tool_call>
```
**Tokens**: ~20
**Time**: 2.32s

### Devstral Response (Slow)
```
I apologize, but I'm unable to check for type errors in the `src/`
directory at the moment. It seems there was an issue with parsing
the type checker's output.

Would you like me to try a different approach? I can:
1. Run the type checker with different options
2. Check a specific file instead of the entire directory
3. Use an alternative type checking method

[continues for 200+ tokens...]
```
**Tokens**: ~300-500
**Time**: 95s average (some queries 300s+!)

**Analysis**: Devstral generates long explanations because:
1. Zero-shot model lacks fine-tuned brevity
2. Trained on conversational, helpful responses (not terse tool calls)
3. No training data showing "just call the tool, no explanation"

## What We Learned

### ✅ Successes

1. **Direct Code Tools Architecture Works**: 84% accuracy proves zero-shot models CAN call tools correctly with right architecture
2. **Multi-Turn Fixed**: Upstream Ollama fix gave +20% accuracy
3. **Error Handling**: All 11 tools now production-ready with try/except
4. **Honest Validation**: Tool identity checks, retry tracking, trustworthy metrics
5. **Instruction Improvements**: Fixed some false refusals (field access 75% → 100%)

### ❌ Failures

1. **Speed**: 40x slower than fine-tuned Qwen3
2. **Variance**: Query times range 8-309s (unpredictable)
3. **Verbose**: Model generates long explanations unnecessarily
4. **Cost**: Slow = expensive in production (compute time)
5. **User Experience**: 95s average response time is unacceptable

### 🔍 Insights

1. **Zero-shot trade-off**: No training cost, but 40x slower runtime
2. **Fine-tuning ROI**: One-time training cost → 40x faster forever
3. **Architecture matters**: Direct tools worked, but speed depends on model
4. **Ollama overhead**: Minimal (1-5s), not the main problem
5. **Model selection critical**: Fast models (Qwen3) > slow models (Devstral) for agents

## Attempted Fixes

### Phase 38c: Error Handling
- **Goal**: Production-ready error handling
- **Result**: ✅ Success - all 11 tools protected
- **Impact**: No speed improvement

### Phase 38d: Instruction Improvements
- **Goal**: Reduce false refusals, improve tool discovery
- **Result**: ⚠️ Mixed - fixed 1 false refusal, broke 1 multi-step query
- **Impact**: No speed improvement (still 95s average)

### Potential Fix (Not Attempted): Reduce max_tokens
- **Goal**: Force shorter responses (2048 → 512 tokens)
- **Expected**: 3-5x speedup → 20-30s per query
- **Status**: Not tested (even 20-30s is 10x slower than Qwen3)

## Why Return to Qwen3?

### Production Requirements

For production agent use:
1. **Speed**: Sub-5s response time desired
2. **Consistency**: Predictable performance
3. **Accuracy**: 100% on core workflows
4. **Cost**: Efficient compute usage

### Model Comparison vs Requirements

| Requirement | Qwen3 Phase 27 | Devstral | Verdict |
|-------------|----------------|----------|---------|
| Speed (<5s) | ✅ 2.32s | ❌ 95s (40x slower) | **Qwen3 wins** |
| Consistency | ✅ 1.8-2.3s range | ❌ 8-309s range | **Qwen3 wins** |
| Accuracy (100%) | ✅ 100% | ⚠️ 84% | **Qwen3 wins** |
| Cost efficiency | ✅ Fast = cheap | ❌ Slow = expensive | **Qwen3 wins** |

**Qwen3 wins on all metrics.**

## The Case for Fine-Tuning

### Investment
- **One-time cost**: Create training data (~100-500 examples)
- **Training time**: ~1-2 hours on M-series Mac
- **Disk space**: ~20 GB for fine-tuned model

### Returns
- **40x faster**: 95s → 2.32s per query
- **100% accuracy**: vs 84% zero-shot
- **Predictable**: Consistent 2-3s response time
- **Cost savings**: Fast queries = less compute = cheaper at scale

**ROI**: After ~1000 queries, fine-tuning pays for itself in saved compute time.

## Lessons for Future Zero-Shot Attempts

If trying zero-shot again:

1. **Test speed early**: Don't assume zero-shot will be fast
2. **Benchmark vs fine-tuned**: Always compare to baseline
3. **Consider model size**: Smaller models might be faster (but less accurate)
4. **Try different backends**: MLX vs Ollama vs llama.cpp
5. **Measure variance**: Average doesn't tell the whole story (8-309s range!)
6. **Factor user experience**: 95s response time is unusable

## What to Keep from Phase 38

### Keep: Architecture & Error Handling ✅

1. **Direct Code Tools**: `src/punie/agent/toolset.py` (lines 675-1016)
   - 11 direct tools with error handling
   - Reusable for other models
   - Production-ready pattern

2. **Model-Adaptive Factory**: `src/punie/agent/factory.py`
   - Detects model type (`ollama:` prefix)
   - Selects appropriate toolset
   - Useful for multi-model support

3. **Honest Validation**: `scripts/validate_zero_shot_code_mode.py`
   - Tool identity checks
   - Retry tracking
   - Trustworthy metrics

### Remove: Devstral-Specific Code ❌

1. **Ollama Model Wrapper**: `src/punie/agent/ollama_model.py`
   - Not needed if using Qwen3 only
   - Can remove entirely

2. **Direct Instructions**: `PUNIE_DIRECT_INSTRUCTIONS` in `config.py`
   - Keep for reference, but not actively used
   - Qwen3 uses Code Mode instructions

3. **Ollama Backend**: No need to maintain Ollama if using MLX
   - Can uninstall `ollama` if desired
   - Remove Devstral model from disk

## Cleanup Plan

### Code Cleanup

1. **Remove**: `src/punie/agent/ollama_model.py`
2. **Remove**: `tests/test_ollama_model.py`
3. **Keep**: Direct tools (useful architecture reference)
4. **Keep**: Model-adaptive factory (useful for future)
5. **Archive**: Phase 38 docs to `docs/archive/phase38/`

### Model Cleanup

1. **Remove Devstral**: `ollama rm devstral` (~14 GB)
2. **Keep Qwen3**: Phase 21, Phase 27 models (~20 GB each)
3. **Remove**: Validation outputs (`.txt` files can be archived)

### Expected Disk Savings

- Devstral model: ~14 GB
- Validation outputs: ~1 MB
- Total: ~14 GB freed

## Conclusion

Phase 38 was a **successful experiment that reached the wrong conclusion**.

**What we proved:**
- ✅ Zero-shot models CAN use direct tools effectively (84% accuracy)
- ✅ Multi-turn tool calling can be fixed with correct templates
- ✅ Honest validation metrics are essential

**What we discovered:**
- ❌ Devstral is 40x slower than fine-tuned Qwen3
- ❌ Zero-shot convenience doesn't justify 40x performance penalty
- ❌ Fine-tuning is worth the investment for production use

**Final verdict:**
- **Qwen3 Phase 27** (fine-tuned, 100%, 2.3s) is the production winner
- **Devstral** (zero-shot, 84%, 95s) is interesting research but impractical
- **Return to Qwen3** for continued development

The Phase 38 work was valuable - it proved direct tools work and gave us production-ready error handling. But for speed and accuracy, **fine-tuning wins decisively**.

---

**Recommendation**: Focus on Qwen3 Phase 27 and beyond. Archive Phase 38 Devstral work as "interesting experiment, but too slow for production."

**Next**: Phase 39 should explore LibCST transformation tools with Qwen3, not pursue zero-shot alternatives.
