# Shape: Phase 21 — Inference Speed Optimization

## Problem Statement

Phase 20 achieved excellent quality (100% accuracy, 2.61s avg in direct MLX mode) but real-world latency through the PydanticAI → mlx_lm.server pipeline is ~25s for multi-turn tool-calling queries. This is too slow for interactive use.

**Goal:** Reduce end-to-end latency to <10s while maintaining 100% discrimination accuracy.

## Research Questions

1. **Where is the time being spent?**
   - Generation time (model inference)?
   - Tool execution time?
   - Framework overhead (PydanticAI, HTTP, parsing)?
   - Network latency (local server)?

2. **Will speculative decoding help?**
   - How much speedup from draft model verification?
   - What's the optimal `num_draft_tokens` value?
   - Memory impact of running 2 models?
   - Quality impact (hallucinations, accuracy)?

3. **Is verbosity the bottleneck?**
   - Are responses too long?
   - Would conciseness training reduce tokens → faster generation?
   - Can we maintain quality with shorter responses?

## Scope Decisions

### In Scope
- **Profiling:** Build latency breakdown tool (essential for informed decisions)
- **Speculative decoding:** Wire into ServerConfig + benchmark (high-impact, low-risk)
- **Existing model:** Use Phase 20's 5-bit fused Qwen3-30B-A3B (proven quality)
- **5-query test:** Standard discrimination test (maintain 100% accuracy)

### Out of Scope
- **New model architecture:** No switching models (stay on Qwen3-30B-A3B)
- **Quantization changes:** Keep 5-bit (already optimal from Phase 20)
- **Concurrency:** Single-query focus (parallelization is future work)
- **Caching:** No prompt caching or KV cache optimization (complexity vs benefit)

### Conditional
- **Conciseness training:** Only if profiling shows generation time >70% of latency
  - Requires new training data (20-30 tool + 10-15 direct examples)
  - Requires retraining (300 iters, ~2 hours)
  - Risk: might reduce quality

## Implementation Strategy

### Phase 1: Measure (Task 2)
Build `scripts/profile_latency.py` to answer "where is the time?"
- Start real mlx_lm.server via ServerProcess
- Send queries through PydanticAI agent
- Measure: total, generation, tool, overhead
- Output: JSON + human-readable summary

**Decision point:** If generation <70% of total → skip conciseness training

### Phase 2: Optimize (Tasks 3-4)
Wire speculative decoding into ServerConfig + benchmark:
- Add `draft_model`, `num_draft_tokens` fields
- Update `build_server_command()` to use them
- Test with `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` draft
- Compare: baseline vs num_draft_tokens=[2, 3, 5]
- Measure: speed, accuracy, memory

**Decision point:** If speedup <20% → investigate other approaches

### Phase 3: Train (Task 5) — Conditional
Only if profiling + speculative decoding don't hit <10s target:
- Create concise training examples
- Retrain with focus on brevity
- Benchmark token count + latency reduction
- Verify 100% accuracy maintained

### Phase 4: Document (Task 6)
- Update roadmap with results
- Create diary entry
- Update README if production config changes

## Key Constraints

1. **Accuracy:** Must maintain 100% on 5-query discrimination test
2. **Memory:** Must stay within 32GB unified memory (M4 Max)
3. **Quality:** No hallucinations, correct tool usage
4. **Compatibility:** Must work with existing PydanticAI integration

## Success Metrics

- **Primary:** End-to-end latency <10s (multi-turn queries)
- **Secondary:** Speedup % from speculative decoding
- **Quality:** 100% accuracy on discrimination test
- **Memory:** Peak usage <32GB

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Speculative decoding doesn't help | Medium | Profile first to identify bottleneck |
| Draft model reduces quality | High | Benchmark accuracy before deployment |
| Memory pressure (2 models) | Medium | Monitor peak usage, use 4-bit draft |
| Conciseness reduces quality | High | Only pursue if necessary, test thoroughly |

## Reference Implementations

- `src/punie/training/eval_runner.py` — Server lifecycle + agent construction
- `scripts/test_single_model.py` — Direct MLX benchmarking patterns
- `tests/test_training_server_config.py` — Test patterns for new fields
- mlx-lm docs: https://github.com/ml-explore/mlx-examples/tree/main/llms#speculative-decoding

## Open Questions

- What's the actual latency breakdown?
- Does speculative decoding work well with MoE models?
- Is 1.5B draft model the right size?
- Should we test Qwen2.5-Coder-0.5B-Instruct as draft?
