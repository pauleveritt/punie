# Training Experiment Journal

This document tracks all training experiments, evaluations, and decisions for Punie's local model fine-tuning.

## Cumulative Results

| Step | Dataset | Adapter | Overall | Tool Calling | Code Gen | Reasoning | Notes |
|------|---------|---------|---------|-------------|----------|-----------|-------|
| Baseline | — | — | — | — | — | — | Not yet evaluated |

## Experiments

### Phase 12: Server Management Infrastructure (2026-02-11)

**Goal:** Build infrastructure for automated mlx_lm.server lifecycle management.

**What we did:**
- Created `ServerConfig` dataclass for server configuration
- Implemented `ServerProcess` for subprocess lifecycle management
- Added `create_server_model()` factory integration
- Built training speed benchmark utilities
- Created comprehensive test suite (20 tests)

**Commands run:**
```bash
uv run pytest tests/test_training_*.py -v
# All 20 tests passed

uv run ruff check src/punie/training/
# No issues

uv run ty check src/punie/training/
# All type checks passed
```

**Results:**
- ✅ All 320 tests pass (up from 297)
- ✅ 81%+ test coverage maintained
- ✅ All code passes ruff and ty checks
- ✅ Infrastructure ready for Phase 13 (Evaluation Harness)

**Files created:**
- `src/punie/training/__init__.py`
- `src/punie/training/server_config.py`
- `src/punie/training/server.py`
- `src/punie/training/benchmark.py`
- `tests/test_training_server_config.py`
- `tests/test_training_server.py`
- `tests/test_training_benchmark.py`
- `agent-os/specs/2026-02-11-server-management/` (4 files)

**Next steps:**
- Phase 12.4: Run actual benchmark with mlx-lm installed to verify 30B model is trainable
- Phase 13: Build evaluation harness using this infrastructure

---

### Benchmark: Training Speed (Pending)

**Goal:** Verify that LoRA training on Qwen3-Coder-30B-A3B-Instruct-4bit is feasible on M1 32GB.

**Model:** mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit (~15GB, 3B active parameters)

**Command to run:**
```bash
# First, create dummy dataset
uv run python -c "
from pathlib import Path
from punie.training.benchmark import create_dummy_dataset
create_dummy_dataset(Path('data/benchmark'), num_examples=5)
"

# Then run benchmark
uv run python -c "
import asyncio
from punie.training.benchmark import run_training_benchmark

async def main():
    result = await run_training_benchmark(
        model_path='mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit',
        num_iters=10,
    )
    print(f'Model: {result.model_path}')
    print(f'Seconds per iteration: {result.seconds_per_iter:.2f}')
    print(f'Total seconds: {result.total_seconds:.2f}')
    print(f'Iterations: {result.num_iters}')
    if result.peak_memory_gb:
        print(f'Peak memory: {result.peak_memory_gb:.2f} GB')

asyncio.run(main())
"
```

**Decision criteria:**
- ~1-5 sec/iter: ✅ Proceed with 30B (100 iters = 2-8 min, fast iteration)
- ~10-30 sec/iter: ✅ Still usable (100 iters = 15-50 min, acceptable)
- >60 sec/iter: ❌ Pivot to 7B model

**Results:** *(to be filled in after running benchmark)*

---

## Notes

- All experiments should be run from project root
- Update cumulative table after each evaluation
- Include raw command output in experiment entries
- Document any failures or unexpected behavior
- Track dataset versions and adapter paths
