# Training Summary: Deep Testing Phase Complete

**Date:** February 12, 2026
**Branch:** local-model-training
**Status:** ✅ PIPELINE VERIFIED, BASE MODEL IS BEST

## Executive Summary

After comprehensive deep testing and evaluation, we discovered that **the base Qwen2.5-Coder-1.5B-Instruct-4bit model outperforms all fine-tuned versions**. Previous training attempts degraded model performance rather than improving it.

## Key Findings

### 1. Base Model Performance (No Fine-Tuning Needed!)

**Qwen2.5-Coder-1.5B-Instruct-4bit baseline:**
- Overall: **92.9%**
- Code generation: **100%**
- Reasoning: **100%**
- Tool calling: **83.3%**

This is **excellent performance** without any fine-tuning!

### 2. Fine-Tuned Adapters Made Things Worse

| Adapter | Overall | Tool Call | Impact |
|---------|---------|-----------|--------|
| Base (no adapter) | **92.9%** | **83.3%** | ✅ Best |
| qwen-tool-calling | 57.1% | 16.7% | ❌ -35.8% overall |
| tool-calling-synthetic | 32.1% | 33.3% | ❌ -60.8% overall |

**Conclusion:** Existing fine-tuning attempts caused **catastrophic forgetting**.

### 3. Model Size Comparison

**Qwen2.5-1.5B vs Qwen3-30B:**
- 1.5B: 92.9% overall (100% code, 100% reason, 83.3% tools)
- 30B: 75.0% overall (87.5% code, 50.0% reason, 83.3% tools)

The **smaller model is better** on this eval suite! Size isn't everything.

### 4. Different Models Use Different Formats

- **30B Model:** PydanticAI structured calls (no text parsing needed)
- **1.5B Model:** ```json code fences (requires text parser)

Parser now supports both formats (4 formats total).

## What We Verified

✅ **Evaluation Pipeline:**
- Parser works for 4 formats (tags, code fences, XML, broken XML)
- Eval runner correctly uses fallback logic
- Scoring is accurate (17 tests passing)
- HTML reports are trustworthy

✅ **Baseline Metrics:**
- 1.5B: 92.9% overall (our best model)
- 30B: 75.0% overall
- Existing adapters: 16.7% - 33.3% tool calling (worse than base!)

✅ **Training Templates:**
- Fixed format: now use `<tool_call>` tags with `"name"` key
- Aligned with parser expectations
- Ready for future training attempts

## Why Previous Training Failed

Based on adapter evaluation results, the failures were likely due to:

1. **OLD template format** (before our fix)
   - Used ` ```json ``` ` with `"tool"` key
   - Mismatched with parser expectations
   - Caused poor tool calling performance

2. **Catastrophic forgetting**
   - Too much training on narrow task
   - Model forgot general capabilities
   - Lost reasoning and code generation skills

3. **Poor dataset quality**
   - Not enough diversity
   - Too focused on one task
   - Didn't preserve base model strengths

4. **Wrong training parameters**
   - Possibly too many iterations
   - Learning rate too high
   - LoRA rank insufficient

## Recommendations Going Forward

### Recommendation 1: Use Base Model (No Fine-Tuning)

**Rationale:**
- Base 1.5B model already achieves 92.9% overall
- Tool calling at 83.3% is acceptable
- Fine-tuning degraded performance in all attempts
- No training = no risk of catastrophic forgetting

**Action:** Deploy base model directly in production.

### Recommendation 2: If Fine-Tuning is Necessary

**Only proceed if 83.3% tool calling is insufficient.**

**Requirements for success:**
1. **High-quality diverse dataset**
   - 1000+ examples minimum
   - Mix of tool calling AND general code tasks
   - Preserve base model capabilities

2. **Conservative training parameters**
   - Low learning rate (1e-6, not 1e-5)
   - Few iterations (50-100 max)
   - Monitor validation loss closely
   - Stop early if validation increases

3. **Continuous evaluation**
   - Evaluate every 25 iterations
   - Compare against 92.9% baseline
   - Stop immediately if overall drops below 90%

4. **Use NEW template format**
   - `<tool_call>` tags with `"name"` key
   - Matches parser expectations
   - Aligned with evaluation pipeline

### Recommendation 3: Focus on Prompting Instead

**Alternative to fine-tuning:**
- Improve system prompts
- Few-shot examples in context
- Better tool descriptions
- Clearer user instructions

**Benefits:**
- No risk of degrading model
- Faster iteration
- Easier to maintain
- More flexible

## Files Created During Deep Testing

**Test Scripts:**
- `test_tool_calling_deep.py` - Comprehensive pipeline verification (3 tests)
- `test_1.5b_tool_format.py` - Output format diagnostic tool

**Documentation:**
- `docs/research/tool-call-parsing-restoration.md` - Parser restoration record
- `docs/research/deep-test-findings.md` - Complete analysis
- `docs/research/training-readiness.md` - LoRA training preparation
- `docs/research/training-journal.md` - Updated with Phase 18

**Code:**
- `src/punie/training/tool_call_parser.py` - Enhanced with 4 format support
- `tests/test_training_tool_call_parser.py` - 17 tests (all passing)

**Evaluation Reports:**
- `eval_20260212-164452.html` - 30B baseline (75.0%)
- `eval_20260212-164709.html` - 1.5B baseline (92.9%)
- `eval_20260212-165432.html` - 1.5B + qwen-tool-calling (57.1%)
- `eval_20260212-165831.html` - 1.5B + tool-calling-synthetic (32.1%)

## Commits

1. `0630d98` - Restore tool call parser and fix training template format
2. `c60bdb8` - Add deep test suite for tool calling pipeline verification
3. `2fc08b5` - Add code fence support to parser and complete deep testing
4. *(next)* - Final summary and adapter evaluation results

## Metrics Summary Table

| Configuration | Overall | Code Gen | Reasoning | Tool Call | Recommendation |
|---------------|---------|----------|-----------|-----------|----------------|
| **1.5B Base** | **92.9%** | **100%** | **100%** | **83.3%** | **✅ USE THIS** |
| 30B Base | 75.0% | 87.5% | 50.0% | 83.3% | ⚠️ Worse than 1.5B |
| 1.5B + qwen-tc | 57.1% | 100% | 75.0% | 16.7% | ❌ Avoid |
| 1.5B + synthetic | 32.1% | 62.5% | 0.0% | 33.3% | ❌ Avoid |

## Next Steps

### Immediate (Deploy Base Model)
1. ✅ Evaluation pipeline verified
2. ✅ Base model performance measured (92.9%)
3. ✅ Parser supports all formats
4. 🔄 **Decision:** Use base 1.5B model without fine-tuning

### If Fine-Tuning Needed Later
1. Create high-quality diverse dataset (1000+ examples)
2. Use conservative training parameters
3. Monitor validation loss closely
4. Evaluate continuously
5. Stop if performance drops below baseline

### Alternative Approach (Recommended)
1. Improve prompting strategies
2. Add few-shot examples
3. Enhance tool descriptions
4. Test with real users
5. Iterate on UX, not training

## Conclusion

**The base Qwen2.5-Coder-1.5B-Instruct-4bit model is production-ready at 92.9% overall performance.**

Fine-tuning is not necessary and has been shown to degrade performance. If tool calling performance (83.3%) needs improvement, focus on prompting strategies rather than fine-tuning.

The evaluation pipeline is verified, trusted, and ready for future use if needed.

---

**Status:** ✅ COMPLETE - Base model validated, pipeline verified, ready for production deployment.
