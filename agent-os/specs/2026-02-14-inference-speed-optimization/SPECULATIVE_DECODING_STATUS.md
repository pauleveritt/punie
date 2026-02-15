# Speculative Decoding Status

**Date:** 2026-02-14
**Phase:** 21 (Inference Speed Optimization)

## Summary

Speculative decoding infrastructure is **implemented and ready** but **not benchmarked** due to complexity and time constraints. Deferred in favor of Phase 22 (Code Mode) which provides higher-value architectural improvements.

## What's Implemented ✅

1. **ServerConfig Support**
   - Added `draft_model` field (optional path to draft model)
   - Added `num_draft_tokens` field (number of tokens to predict ahead)
   - Default: `None` (disabled)

2. **Command Building**
   - `build_server_command()` passes `--draft-model` flag to mlx_lm.server
   - `build_server_command()` passes `--num-draft-tokens` flag
   - Flags only added when speculative decoding is enabled

3. **Test Infrastructure**
   - `scripts/benchmark_speculative.py` - Comprehensive benchmark (4 configs, 5 queries each)
   - Tests: baseline, 2 tokens, 3 tokens, 5 tokens
   - Draft model: `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` (1GB)
   - Measures: latency, accuracy, memory usage

4. **Tests Passing**
   - 29 tests in test_training_server.py and test_training_server_config.py
   - ServerConfig correctly stores draft parameters
   - Command builder correctly generates flags
   - Type checking (ty) and linting (ruff) pass

## What's Not Done ❌

1. **Benchmarking**
   - Benchmark script times out or hangs (model loading complexity)
   - Multiple server instances difficult to manage
   - Unclear if speculative decoding works well with MoE models (Qwen3-30B-A3B)

2. **Production Validation**
   - No empirical data on speedup with Phase 21 model
   - No validation of accuracy preservation
   - No memory overhead measurement

## Why Deferred?

### Complexity
- Loading multiple models (30B main + 1.5B draft) is resource intensive
- Server management for 4 different configs is complex
- Benchmark script requires async coordination of multiple servers

### Uncertain ROI
- Speculative decoding typically: 1.5-2x speedup
- Current latency: ~6.6s per tool query (already acceptable)
- MoE models (like Qwen3) may not benefit as much (already fast per active param)
- Potential speedup: 6.6s → 3-4s (diminishing returns)

### Higher-Value Alternative: Phase 22 (Code Mode)

**Phase 22 provides bigger wins:**
1. **Format elimination** - No more XML/JSON parsing fragility
2. **Multi-step efficiency** - N tools in 1 turn (vs N+2 turns now)
3. **Type safety** - ty integration for correctness
4. **Architectural simplicity** - Python code is easier to reason about
5. **Industry validated** - Anthropic, Cloudflare, Pydantic converged on this

**Phase 22 potential impact:**
- Multi-tool queries: N+2 model turns → 1 model turn (massive latency reduction)
- Example: "Find all tests, count functions in each"
  - Current: User query → model (tool) → execute → model (tool) → execute → model (answer) = 5 turns
  - Code Mode: User query → model (Python loop) → answer = 2 turns

## Recommendation

**Skip speculative decoding benchmarking for now:**
1. Infrastructure is ready if needed later
2. Current 6.6s latency is acceptable
3. Phase 22 Code Mode has higher architectural value
4. Can revisit if latency becomes critical

**How to use speculative decoding (when needed):**
```python
from punie.training.server_config import ServerConfig

config = ServerConfig(
    model_path="fused_model_qwen3_phase21_xml_5bit",
    draft_model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    num_draft_tokens=3,  # Sweet spot typically 2-4
    port=8080,
)

# Server will automatically use speculative decoding
```

## References

- MLX speculative decoding: https://github.com/ml-explore/mlx-examples/tree/main/llms/mlx_lm#speculative-decoding
- Qwen3-30B-A3B: MoE model (30B total, 3.3B active per token)
- Draft model: Qwen2.5-Coder-1.5B-Instruct-4bit (~1GB)
- Phase 22 planning: `agent-os/product/roadmap.md` (Code Mode)

## Future Work

If latency becomes critical:
1. **Simplify benchmark** - Test single config (3 draft tokens) vs baseline
2. **Manual validation** - Start server with draft model, time queries manually
3. **Document trade-offs** - Memory overhead vs latency reduction
4. **Production testing** - Real workload validation (not synthetic queries)

---

**Status:** Infrastructure complete ✅ | Benchmarking deferred ⏸️ | Ready for Phase 22 🚀
