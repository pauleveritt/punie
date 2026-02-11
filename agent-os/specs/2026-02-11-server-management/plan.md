# Server Management Spec - Plan

## Goal

Automate starting/stopping `mlx_lm.server` from Python so evaluation and training can be fully scripted. All code launches mlx-lm as a subprocess — no import-time dependency on mlx-lm. All tests work without it installed.

## Components

### 12.1: Server configuration dataclass

- `ServerConfig` (frozen): model_path, port, host, adapter_path, max_kv_size, repetition_penalty
- `base_url` property for OpenAI-compatible API endpoint
- Pure dataclass, easily tested

### 12.2: Server process lifecycle

- `build_server_command(config) -> list[str]` — pure function, easily tested
- `ServerProcess` (non-frozen dataclass, like `LocalClient` pattern):
  - `async start(timeout)` — launch subprocess, poll `/v1/models` until ready
  - `async stop(timeout)` — SIGTERM, wait, SIGKILL if needed
  - `async health_check() -> bool` — GET `/v1/models`
  - `is_running` property
  - async context manager support

### 12.3: Integration with factory

- `create_server_model(config) -> Model` — thin wrapper using `OpenAIProvider` + `OpenAIChatModel`
- Follows same pattern as `_create_local_model()`

### 12.4: Training speed benchmark

- `create_dummy_dataset(directory, num_examples)` — writes tiny train/valid/test JSONL
- `run_training_benchmark(model_path, num_iters) -> BenchmarkResult` — measures LoRA training speed
- `BenchmarkResult` (frozen): seconds_per_iter, total_seconds, num_iters, peak_memory_gb
- User verification before committing to 30B model (pivot to 7B if too slow)

## Success Criteria

- All existing 297+ tests still pass
- All new tests pass
- `build_server_command()` produces correct args
- Benchmark gives real timing numbers
- Coverage stays above 80%
