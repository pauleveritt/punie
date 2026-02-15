# Plan: Phase 21 — Inference Speed Optimization

## Context

Phase 20 achieved a Qwen3-30B-A3B MoE migration with 5-bit quantization (20GB, 100% accuracy, 2.61s avg per query in direct MLX mode). However, end-to-end latency through the full PydanticAI → mlx_lm.server pipeline is ~25s for tool-calling queries (2+ generation turns). The goal is to reduce this to <10s while maintaining 100% discrimination accuracy.

A recent commit (`5a6e8c6`) replaced invalid `ServerConfig` flags with real mlx-lm 0.30.6 flags (`temp`, `top_p`, `max_tokens`, `chat_template_args`). Speculative decoding support is available in mlx-lm but not yet wired into Punie.

User's priority order: **Profile first** → **speculative decoding** → **conciseness training**.

## Key Findings

- **mlx-lm v0.30.6** supports `--draft-model` and `--num-draft-tokens` server flags
- **ServerConfig** (`server_config.py`) has `temp`, `top_p`, `max_tokens`, `chat_template_args` — no speculative decoding fields yet
- **build_server_command()** (`server.py`) follows clear pattern for optional flags — easy to extend
- **No latency breakdown** exists — can't tell where time is spent
- **Command format:** `python -m mlx_lm server` (not deprecated `python -m mlx_lm.server`)
- **435 tests passing**, 0 ruff errors (clean baseline)

## Critical Files

- `src/punie/training/server_config.py` — Add `draft_model`, `num_draft_tokens`
- `src/punie/training/server.py` — Add flags to `build_server_command()`
- `tests/test_training_server_config.py` — 12 existing tests, follow same pattern
- `tests/test_training_server.py` — 12 existing tests, follow same pattern
- `src/punie/training/eval_runner.py` — Evaluation harness (realistic benchmark)
- `scripts/test_single_model.py` — Direct MLX benchmark (reuse patterns)

## Tasks

### Task 1: Save spec documentation ✅

Create `agent-os/specs/2026-02-14-inference-speed-optimization/` with:
- `plan.md` — This plan
- `shape.md` — Shaping notes (scope, decisions, context)
- `standards.md` — agent-verification standard
- `references.md` — Reference implementations

### Task 2: Create end-to-end latency profiler

Create `scripts/profile_latency.py` that measures breakdown through the real pipeline:

1. Start `mlx_lm` server with 5-bit fused model via `ServerProcess`
2. Send queries through PydanticAI agent (same path as production)
3. Measure and report per query:
   - **Total end-to-end time**
   - **Generation time** (time in HTTP call to mlx_lm.server)
   - **Tool execution time** (if tool-calling query)
   - **Framework overhead** (PydanticAI processing, tool parsing)
4. Run the standard 5-query discrimination test
5. Output JSON results + human-readable summary

Reuse patterns from `src/punie/training/eval_runner.py` (server lifecycle + agent construction).

### Task 3: Wire speculative decoding into ServerConfig

**`src/punie/training/server_config.py`** — Add 2 fields:
```python
draft_model: str | None = None       # Draft model for speculative decoding (--draft-model)
num_draft_tokens: int | None = None  # Tokens per draft step (--num-draft-tokens)
```

**`src/punie/training/server.py`** — Add to `build_server_command()`:
```python
if config.draft_model is not None:
    cmd.extend(["--draft-model", config.draft_model])
if config.num_draft_tokens is not None:
    cmd.extend(["--num-draft-tokens", str(config.num_draft_tokens)])
```

**`tests/test_training_server_config.py`** — Add tests following existing pattern:
- `test_server_config_with_draft_model()`
- `test_server_config_with_num_draft_tokens()`
- Update `test_server_config_defaults()` and `test_server_config_all_parameters()`

**`tests/test_training_server.py`** — Add tests:
- `test_build_server_command_with_draft_model()`
- `test_build_server_command_with_num_draft_tokens()`
- Update `test_build_server_command_all_parameters()`

### Task 4: Benchmark speculative decoding

Create `scripts/benchmark_speculative.py` that:

1. **Baseline:** 5-query test with 5-bit fused model (no draft)
2. **Speculative:** Same test with `draft_model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"`
3. Test `num_draft_tokens` values: 2, 3, 5
4. Compare: speed, accuracy, memory

**Disk note:** 1.5B draft model ~1GB (from HF cache). Total: ~21GB.

### Task 5: Train for conciseness (conditional)

Only if profiling shows generation time >70% of total latency:

1. Create 20-30 concise tool-calling examples
2. Create 10-15 concise direct-answer examples
3. Retrain and benchmark token count reduction

### Task 6: Update roadmap and documentation

- Update `agent-os/product/roadmap.md` Phase 21 with results
- Create diary entry with findings
- Update README if production config changes

## Verification

1. Use `astral:ty` skill to check types
2. Use `astral:ruff` skill to check and fix linting
3. Run `uv run pytest tests/` to verify all tests pass
4. Run profiler to verify latency breakdown
5. Run speculative decoding benchmark to verify speedup
6. Verify 100% accuracy maintained on 5-query discrimination test

## Success Criteria

- [ ] End-to-end latency reduced from ~25s to <10s
- [ ] 100% accuracy maintained on 5-query discrimination test
- [ ] Memory usage remains within 32GB unified memory budget
- [ ] All tests pass (435+)
- [ ] Clean ruff + ty output
- [ ] Documentation updated with results
