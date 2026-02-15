# Standards: Phase 21 — Inference Speed Optimization

## Agent Verification Standard

This spec follows the `agent-verification` standard for systematic implementation with automated checks.

### Code Quality

**Type checking:**
```bash
uv run ty src/punie/training/server_config.py
uv run ty src/punie/training/server.py
uv run ty scripts/profile_latency.py
uv run ty scripts/benchmark_speculative.py
```

**Linting:**
```bash
uv run ruff check src/punie/training/
uv run ruff check scripts/profile_latency.py
uv run ruff check scripts/benchmark_speculative.py
```

**Formatting:**
```bash
uv run ruff format src/punie/training/
uv run ruff format scripts/
```

### Testing

**Unit tests:**
```bash
uv run pytest tests/test_training_server_config.py -v
uv run pytest tests/test_training_server.py -v
```

**Full test suite:**
```bash
uv run pytest tests/ --tb=short
```

**Expected:** 435+ tests passing, 0 failures

### Functional Verification

**Baseline profiling:**
```bash
uv run python scripts/profile_latency.py
```

**Expected output:**
- JSON file with latency breakdown
- Human-readable summary
- 5/5 queries successful

**Speculative decoding benchmark:**
```bash
uv run python scripts/benchmark_speculative.py
```

**Expected output:**
- Baseline vs speculative comparison
- num_draft_tokens=[2,3,5] results
- Speed improvement %
- 5/5 accuracy maintained

### Performance Criteria

**Latency targets:**
- End-to-end: <10s (down from ~25s)
- Speedup: >60% improvement
- Accuracy: 100% (5/5 on discrimination test)

**Memory constraints:**
- Peak usage: <32GB unified memory
- Baseline (5-bit main): ~20GB
- With draft (4-bit 1.5B): ~21GB total

**Quality gates:**
- All tests passing
- No ruff errors
- No type errors
- 100% discrimination accuracy

## Test Coverage Requirements

### ServerConfig Tests
- `test_server_config_with_draft_model()` — draft_model field
- `test_server_config_with_num_draft_tokens()` — num_draft_tokens field
- Update `test_server_config_defaults()` — new fields = None
- Update `test_server_config_all_parameters()` — include new fields

### Server Command Tests
- `test_build_server_command_with_draft_model()` — --draft-model flag
- `test_build_server_command_with_num_draft_tokens()` — --num-draft-tokens flag
- Update `test_build_server_command_all_parameters()` — include new flags

### Profiler Tests
- Latency breakdown accuracy (generation + tool + overhead = total)
- JSON output format validation
- Server lifecycle management
- Error handling (server fails, timeout)

### Benchmark Tests
- Baseline vs speculative comparison
- Multiple num_draft_tokens values
- Accuracy preservation (5/5 on standard test)
- Memory usage tracking

## Documentation Requirements

**Code documentation:**
- Docstrings for new fields (draft_model, num_draft_tokens)
- Comments explaining speculative decoding flags
- Type hints for all new functions

**Spec documentation:**
- plan.md — Implementation tasks ✅
- shape.md — Scope, decisions, constraints ✅
- standards.md — This file ✅
- references.md — External references ✅

**Project documentation:**
- Update `agent-os/product/roadmap.md` Phase 21
- Create diary entry with results
- Update README.md if production config changes

## Git Workflow

**Branch:** `phase-21-inference-speed`

**Commits (when requested):**
1. "Add spec documentation for Phase 21"
2. "Add latency profiler for end-to-end benchmarking"
3. "Wire speculative decoding into ServerConfig"
4. "Add benchmark for speculative decoding"
5. "Update roadmap and documentation with Phase 21 results"

**No auto-commit:** Always ask user before creating commits (per CLAUDE.md)

## Verification Checklist

Before marking tasks complete:

- [ ] Code passes type checking (ty)
- [ ] Code passes linting (ruff)
- [ ] All tests pass (pytest)
- [ ] Profiler outputs valid JSON + summary
- [ ] Benchmark shows speedup + maintains accuracy
- [ ] Memory usage <32GB
- [ ] Documentation updated
- [ ] Roadmap updated with results
