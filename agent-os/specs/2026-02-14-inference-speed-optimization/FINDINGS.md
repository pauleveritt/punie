# Phase 21 Findings

## Date: 2026-02-14

## Critical Issue Discovered: Tool-Calling Behavior Lost in Fused Models

### Problem

When running the latency profiler (`scripts/profile_latency.py`) against the 5-bit fused model (`fused_model_qwen3_phase8_5bit`), the model **failed to call tools** for queries that should trigger tool usage.

### Results

**Latency (Good News):**
- Average per query: 4.0s
- Much better than expected ~25s for multi-turn queries
- Breakdown: 98% generation, 2% framework overhead

**Accuracy (Critical Issue):**
- **40% (2/5 queries correct)**
- ❌ Failed all 3 tool-calling queries (Find Django views, Show UserSerializer, Find async/await)
- ✅ Passed 2 direct-answer queries (dependency injection, ORM vs SQL)
- Model gave direct answers instead of calling tools

### Comparison to Phase 20 Results

**Phase 20 claimed:**
- "5-bit (32 levels): ✅ Preserves LoRA signal → 100% accuracy (threshold)"

**Current results:**
- 5-bit → 40% accuracy (tool calling broken)

### Hypothesis

The 5-bit quantization threshold may be too aggressive for **tool-calling behavior**, which is more complex than simple discrimination tasks. Possible explanations:

1. **Tool-calling instructions more fragile:** Tool-calling requires precise understanding of when/how to format tool calls, which may require higher precision than general question answering
2. **Fusion process issue:** The fusion/quantization process may have specifically damaged tool-calling weights
3. **Test methodology:** Phase 20 may have tested with simpler queries or different evaluation criteria

### Evidence

**Test queries attempted:**
1. "Find all Django view functions" → Expected: `run_command` tool → Got: Direct answer ❌
2. "Show me the implementation of UserSerializer" → Expected: `read_file` tool → Got: Direct answer ❌
3. "Find all uses of async/await in the codebase" → Expected: `run_command` tool → Got: Direct answer ❌

All queries returned direct answers (often saying "I don't have access to your codebase") instead of calling the appropriate tools.

### Impact on Phase 21

**Blocked:**
- ❌ Cannot proceed with speculative decoding benchmark (requires working tool calling)
- ❌ Cannot measure true end-to-end latency (tools never executed)
- ❌ 5-bit model not production-ready for tool-calling use case

**Not Blocked:**
- ✅ Infrastructure is complete (ServerConfig, profiler, benchmark scripts all work)
- ✅ Can test adapter-based approach (not fused)
- ✅ Can test higher quantization (6-bit, 8-bit)

### Next Steps

**Immediate Investigation Required:**

1. **Test adapter-based approach** (not fused)
   - Run profiler with Phase 8 adapter + base model
   - Verify tool-calling works with adapters
   - Measure latency with adapter loading overhead

2. **Test higher quantization levels**
   - Try 6-bit fused model
   - Try 8-bit fused model
   - Find threshold where tool-calling is preserved

3. **Compare training vs inference formats**
   - Check if tool-calling format in training data matches inference expectations
   - Verify Qwen3 chat template handles tools correctly

4. **Fallback: Use adapter instead of fusion**
   - If fusion consistently breaks tool calling, stay with adapter approach
   - Accept slower load time for correct behavior

### Files

- Profiler: `scripts/profile_latency.py`
- Results: `logs/latency_profile.json`
- Test script: `scripts/test_8bit_model.py` (created during investigation)

### Recommendation

**Do not proceed with Phase 21 completion** until tool-calling is fixed. The 4.0s latency is excellent, but meaningless if the model doesn't call tools.

**Priority 1:** Determine why fusion breaks tool-calling and find a quantization level (or alternative approach) that preserves this critical behavior.
