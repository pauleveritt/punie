# Local Model Fine-Tuning Infrastructure

## Context

Punie currently connects to local models via OpenAI-compatible API (LM Studio / mlx-lm.server) but has zero training infrastructure. The direct MLX model loading code was removed in Phase 11. The `local-model-training` branch is clean and ready for this work.

The approach is slow, methodical, and documented: build measurement machinery first, get training data second, tune conservatively third. Every step must be independently verifiable and must not break existing tests (297 collected, 81%+ coverage).

**Base model decision:** Qwen3-Coder-30B-A3B-Instruct-4bit (~15GB). This is the only model that successfully did tool calling in local testing. It's a Mixture of Experts model with only ~3B active parameters per forward pass, which means training speed may be closer to a 3B model despite 30B total. Phase 12 includes an early benchmark to confirm training is feasible on M1 32GB before we commit further. If benchmarks show it's too slow, we pivot to 7B.

---

## Phase 12: Server Management

**Goal:** Automate starting/stopping `mlx_lm.server` from Python so evaluation and training can be fully scripted.

All code launches mlx-lm as a **subprocess** — no import-time dependency on mlx-lm. All tests work without it installed.

### 12.1: Server configuration dataclass

**New:** `src/punie/training/__init__.py`, `src/punie/training/server_config.py`

```python
@dataclass(frozen=True)
class ServerConfig:
    model_path: str  # e.g., "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
    port: int = 8080
    host: str = "127.0.0.1"
    adapter_path: str | None = None  # LoRA adapter directory (None = base model)
    max_kv_size: int | None = None  # KV cache limit (memory vs. context tradeoff)
    repetition_penalty: float | None = None  # Inference-time repetition penalty

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/v1"
```

**New:** `tests/test_training_server_config.py` — frozen, defaults, base_url, adapter_path tests (all pure)

### 12.2: Server process lifecycle

**New:** `src/punie/training/server.py`

- Pure function `build_server_command(config) -> list[str]` — easily tested
- `ServerProcess` (non-frozen dataclass, like `LocalClient` pattern):
  - `async start(timeout=60.0)` — launch subprocess, poll `/v1/models` until ready
  - `async stop(timeout=10.0)` — SIGTERM, wait, SIGKILL if needed
  - `async health_check() -> bool` — GET `/v1/models`
  - `is_running` property
  - async context manager (`__aenter__`/`__aexit__`)

**New:** `tests/test_training_server.py` — command builder tests (pure), initial state tests, idempotent stop, health_check to unreachable port

### 12.3: Integration with factory

**Modify:** `src/punie/agent/factory.py` — add `create_server_model(config: ServerConfig) -> Model` thin wrapper using same `OpenAIProvider` + `OpenAIChatModel` pattern as `_create_local_model()`

### 12.4: Training speed benchmark

Before building the full evaluation harness, verify LoRA training is feasible on M1 32GB with the 30B model.

**New:** `src/punie/training/benchmark.py`

- `create_dummy_dataset(directory: Path, num_examples: int = 5) -> None` — writes tiny train/valid/test JSONL files with simple chat-completion examples
- `async run_training_benchmark(model_path: str, num_iters: int = 10) -> BenchmarkResult` — runs `mlx_lm.lora` on the dummy data, measures wall-clock time per iteration and peak memory

```python
@dataclass(frozen=True)
class BenchmarkResult:
    model_path: str
    seconds_per_iter: float
    total_seconds: float
    num_iters: int
    peak_memory_gb: float | None  # From psutil if available
```

**New:** `tests/test_training_benchmark.py` — test `create_dummy_dataset()` writes valid JSONL (uses tmp_path, no mlx-lm needed)

**User verification:** Run the benchmark manually with mlx-lm installed:
- If ~1-5 sec/iter: proceed with 30B (100 iters = 2-8 min, fast iteration)
- If ~10-30 sec/iter: still usable (100 iters = 15-50 min, acceptable)
- If >60 sec/iter: pivot to 7B model

### 12.5: Spec + roadmap

**New:** `agent-os/specs/2026-02-11-server-management/` (plan.md, shape.md, standards.md, references.md)
**Modify:** `agent-os/product/roadmap.md` — Phase 12 entry

**Verify:** All existing tests pass. New tests pass. `build_server_command()` produces correct args. Benchmark gives real timing numbers.

---

## Phase 13: Evaluation Harness

**Goal:** Run standardized prompts against a model, score results, produce a baseline report. The evaluation loop (start server → run prompts → measure → stop server) is the foundation everything else builds on.

### 13.1: Evaluation prompt dataclass

**New:** `src/punie/training/eval_prompts.py`

- `EvalPrompt` (frozen): id, category, prompt_text, expected_tool_calls, expected_keywords
- `EvalSuite` (frozen): name, prompts tuple, `by_category()` filter

**New:** `src/punie/training/eval_suites.py` — `create_baseline_suite()` factory returning 5-10 prompts across categories: `tool_calling`, `code_generation`, `reasoning`

**New:** `tests/test_training_eval_prompts.py` — frozen, filtering, categories, unique IDs

### 13.2: Evaluation results + scoring

**New:** `src/punie/training/eval_results.py`

- `EvalResult` (frozen): prompt_id, response_text, tool_calls_made, duration_ms, score, success
- `EvalReport` (frozen): model_name, adapter_path, suite_name, timestamp, results tuple
  - `overall_score`, `score_by_category()`, `success_rate` properties

**New:** `src/punie/training/eval_scoring.py` — pure functions:

- `score_tool_calling(prompt, response, tool_calls) -> float` — fraction of expected tools called
- `score_keyword_presence(prompt, response) -> float` — fraction of expected keywords found
- `score_prompt(prompt, response, tool_calls) -> float` — combined score

**New:** `tests/test_training_eval_results.py`, `tests/test_training_eval_scoring.py` — all pure, no server

### 13.3: Evaluation runner

**New:** `src/punie/training/eval_runner.py`

- `EvalRunConfig` (frozen): server_config, suite, workspace, manage_server flag
- `async run_evaluation(config) -> EvalReport` — orchestrates the full loop:
  1. Optionally start server via `ServerProcess`
  2. Create agent via `create_server_model()`
  3. Run each prompt, extract tool calls from messages, score
  4. Stop server
  5. Return frozen `EvalReport`

Unit tests use `model="test"` + `manage_server=False`. Integration tests marked `@pytest.mark.slow`.

### 13.4: HTML report

**New:** `src/punie/training/eval_report.py` — `generate_eval_html_report(report) -> str`

Follows `src/punie/perf/report.py` pattern: standalone HTML, summary, category breakdown, individual results table.

### 13.5: CLI command

**Modify:** `src/punie/cli.py` — add `punie eval` command with `--model`, `--port`, `--suite`, `--no-server` flags

### 13.6: Spec + roadmap

**New:** `agent-os/specs/2026-02-11-evaluation-harness/`
**Modify:** `agent-os/product/roadmap.md` — Phase 13 entry

**Verify:** `uv run punie eval --model test --no-server` produces HTML report. When mlx-lm available, real baseline report with actual scores.

---

## Phase 14: Training Data Infrastructure + LoRA Runner

**Goal:** Framework for managing, validating, filtering, and writing training datasets in MLX LoRA format. Plus the training runner itself. No actual datasets downloaded yet — just the machinery.

### 14.1: Dataset dataclasses

**New:** `src/punie/training/dataset.py`

- `ChatMessage` (frozen): role, content
- `TrainingExample` (frozen): messages tuple, `to_jsonl_dict()`
- `TrainingDataset` (frozen): name, version, train/valid/test tuples
- `DatasetStats` (frozen): total_examples, examples_per_split, avg_message_count, categories breakdown

### 14.2: Validation + filtering

**New:** `src/punie/training/dataset_validation.py` — pure functions:

- `validate_example(example) -> list[str]` — checks message count, last role is assistant, valid roles
- `validate_dataset(dataset) -> list[str]` — checks non-empty splits, validates each example

**New:** `src/punie/training/dataset_filters.py` — pure functions for progressive pruning:

- `filter_by_language(examples, language="en") -> tuple[kept, removed]` — remove non-English content
- `filter_by_python_version(examples, min_version="3.10") -> tuple[kept, removed]` — detect and remove Python 2 / old Python patterns (print statements without parens, `has_key()`, `xrange`, old-style classes, missing type hints as heuristic for age)
- `filter_by_content_quality(examples, min_messages=2) -> tuple[kept, removed]` — remove too-short or malformed examples
- `FilterReport` (frozen): filter_name, kept_count, removed_count, sample_removed — for documenting what each filter step did

Each filter returns both kept and removed examples so we can inspect what was pruned.

### 14.3: JSONL I/O

**New:** `src/punie/training/dataset_io.py`

- `write_dataset(dataset, directory)` — writes `train.jsonl`, `valid.jsonl`, `test.jsonl`
- `read_dataset(directory) -> TrainingDataset` — reads back
- `write_jsonl()` / `read_jsonl()` — low-level
- `compute_stats(dataset) -> DatasetStats` — summary of a dataset

### 14.4: LoRA training runner

**New:** `src/punie/training/lora_config.py`

- `LoRAConfig` (frozen): base_model, data_directory, output_directory, num_iters, batch_size, learning_rate, lora_rank, lora_layers

**New:** `src/punie/training/train_runner.py`

- `build_train_command(config) -> list[str]` — pure function
- `async run_training(config) -> Path` — subprocess execution, returns adapter path

### 14.5: CLI commands

**Modify:** `src/punie/cli.py`:
- `punie train <data-dir>` — run LoRA training
- `punie dataset validate <dir>` — validate a dataset
- `punie dataset stats <dir>` — show dataset statistics

**Modify:** `pyproject.toml` — add `mlx-lm>=0.30.0` as regular dependency

### 14.6: Tests

**New:** `tests/test_training_dataset.py` — frozen, to_jsonl_dict, validation, roundtrip via tmp_path
**New:** `tests/test_training_dataset_filters.py` — each filter function with known inputs/outputs (all pure)
**New:** `tests/test_training_lora_config.py` — frozen, defaults, build_train_command (pure)

**Verify:** Can write, read, validate, filter, and produce stats for a dataset. Filter functions correctly identify Python 2 patterns, non-English content, etc.

---

## Phase 15: General Data — Download + Progressive Pruning

**Goal:** Download ethical general datasets, then progressively prune them step by step, training and measuring at each step. This is the least-risky starting point.

### 15.1: Dataset download scripts

**New:** `src/punie/training/downloaders.py` — functions using `datasets` library (HuggingFace):

- `download_dolma_wiki(output_dir, max_examples=10000)` — Dolma Wikipedia slice (ODC-By, AI2, no LLM-generated content). Technical English about programming.
- `download_redpajama_stackexchange(output_dir, max_examples=10000)` — RedPajama StackExchange Python Q&A (Apache 2.0, real human Q&A, CC-BY-SA)
- `download_kodcode_python(output_dir, max_examples=10000)` — KodCode Python verified subset (execution-verified code, check generation model first)

Each downloader:
1. Streams the dataset (never downloads full corpus)
2. Converts to `TrainingExample` format (chat-completion messages)
3. Writes JSONL to output directory
4. Returns `DatasetStats` summary

**New:** `tests/test_training_downloaders.py` — test the conversion logic with mock data (don't actually download)

**Modify:** `pyproject.toml` — add `datasets>=3.0.0` dependency (HuggingFace datasets library)

### 15.2: Download + inspect raw data

CLI workflow the user follows:
```bash
uv run punie dataset download dolma-wiki --max 5000 --output data/raw/dolma-wiki/
uv run punie dataset download redpajama-python --max 5000 --output data/raw/redpajama/
uv run punie dataset stats data/raw/dolma-wiki/
uv run punie dataset stats data/raw/redpajama/
```

**User verification:** Inspect raw data, confirm it looks reasonable.

### 15.3: Progressive pruning — step by step

Each step produces a new dataset directory and a filter report. Train + eval after each step.

**Step A: Remove non-English**
```bash
uv run punie dataset filter data/raw/dolma-wiki/ --language en --output data/filtered/step-a/
uv run punie dataset stats data/filtered/step-a/
# Train
uv run punie train data/filtered/step-a/ --iters 100 --output adapters/step-a/
# Evaluate
uv run punie eval --adapter adapters/step-a/ --port 8080
```

**Step B: Remove Python 2 code**
```bash
uv run punie dataset filter data/filtered/step-a/ --min-python 3 --output data/filtered/step-b/
uv run punie train data/filtered/step-b/ --iters 100 --output adapters/step-b/
uv run punie eval --adapter adapters/step-b/ --port 8080
```

**Step C: Remove Python < 3.10**
```bash
uv run punie dataset filter data/filtered/step-b/ --min-python 3.10 --output data/filtered/step-c/
uv run punie train data/filtered/step-c/ --iters 100 --output adapters/step-c/
uv run punie eval --adapter adapters/step-c/ --port 8080
```

**Step D: Add user's hand-authored examples**

User authors additional examples (supplementing, not replacing). Merge with filtered data:
```bash
uv run punie dataset merge data/filtered/step-c/ data/hand-authored/general/ --output data/merged/general-v1/
uv run punie train data/merged/general-v1/ --iters 100 --output adapters/general-v1/
uv run punie eval --adapter adapters/general-v1/ --port 8080
```

### 15.4: Hyperparameter tuning

After finding a good dataset through pruning, tune LoRA training parameters. Each run produces a different adapter, evaluated with the same suite.

**Parameters to tune (in priority order):**
1. **Learning rate** — try 1e-5, 5e-5, 1e-4 (most impactful)
2. **LoRA rank** — try r=4, r=8, r=16 (capacity vs. speed tradeoff)
3. **Number of iterations** — plot val loss curve, find where it plateaus
4. **LoRA layers** — which transformer layers get adapters (first N, last N, every other)

**New:** `src/punie/training/hyperparam.py`

- `HyperparamGrid` (frozen): defines parameter combinations to try
- `async run_hyperparam_search(grid, base_config) -> list[tuple[LoRAConfig, EvalReport]]` — runs each combo, returns config+results pairs sorted by score

**Training monitoring:**
- `mlx_lm.lora` logs train/val loss per iteration to stdout — capture and parse this
- `TrainingLog` (frozen): iteration, train_loss, val_loss per step
- `parse_training_log(output: str) -> tuple[TrainingLog, ...]` — pure function
- Plot loss curves in the HTML report (val loss going up = overfitting, stop early)

### 15.5: Inference parameter tuning

After finding a good adapter, tune serving parameters:

- **Temperature** — try 0.0, 0.1, 0.3, 0.7 (lower = more deterministic for code)
- **Top-p** — try 0.9, 0.95, 1.0
- **Repetition penalty** — try 1.0, 1.1, 1.2
- **Max KV cache size** — mlx-lm.server `--max-kv-size` flag

These are ServerConfig/AgentConfig parameters, not training parameters. Evaluated via the same eval harness — just different server launch flags.

### 15.6: Comparison report

After each step, the eval report includes the adapter_path so we can compare scores across steps. Add a simple comparison view:

**New:** `src/punie/training/eval_comparison.py` — `compare_reports(reports: list[EvalReport]) -> str` — side-by-side HTML table showing score progression across pruning steps

**Verify:** At each step, user can see whether pruning improved or hurt model performance.

---

## Phase 16: Tool Calling Data — Download + Tune

**Goal:** Download tool-calling dataset, filter for Python, combine with Punie-specific hand-authored examples, fine-tune, measure.

### 16.1: Toucan dataset download

**New function in** `src/punie/training/downloaders.py`:

- `download_toucan_python(output_dir, max_examples=10000)` — Toucan tool-calling trajectories filtered for Python tasks (Apache 2.0, Salesforce Research, Tier 2 — verify generation model)

Before downloading: run the `audit_dataset_provenance()` verification from `retraining-llms.md` to confirm ethical sourcing.

### 16.2: Tool calling templates + hand-authored data

**New:** `src/punie/training/tool_calling_templates.py` — helper functions for creating multi-turn tool-call training examples in correct format (system → user → assistant w/ tool_call → tool_result → assistant)

Specific to Punie's 7 tools: read_file, write_file, run_command, get_terminal_output, release_terminal, wait_for_terminal_exit, kill_terminal

**New:** `data/hand-authored/tool-calling/` — user creates examples demonstrating correct tool calling for each tool

### 16.3: Progressive training

Same pruning + measure workflow:
1. Download Toucan Python subset → stats
2. Filter non-English, low-quality → train → eval
3. Merge with hand-authored tool-calling examples → train → eval
4. Compare scores against general-data adapter (Phase 15)

### 16.4: Adapter composition

Investigate whether to:
- Train tool-calling adapter on TOP of general-adapted model
- Or combine both datasets and train a single adapter (with data mixing ratio tuning)
- Compare both approaches via evaluation harness

### 16.5: Post-training — merge and re-quantize

Once we have a good adapter:

1. **Merge adapter into base model** — `mlx_lm.fuse --model <base> --adapter-path <adapter> --output <fused>` produces a full model with LoRA weights baked in (faster inference, no adapter overhead)
2. **Re-quantize merged model** — `mlx_lm.convert --quantize --model <fused>` back to 4-bit
3. **A/B test** — compare adapter-applied vs. merged-and-requantized via eval harness (should score identically, but merged is faster)

**New:** `src/punie/training/fuse.py`
- `build_fuse_command(base_model, adapter_path, output_dir) -> list[str]` — pure function
- `async run_fuse(base_model, adapter_path, output_dir) -> Path` — subprocess execution

---

## Phase 17: Advanced Ideas (Placeholder)

Future exploration, no implementation now:
- Self-play training data generation
- Curriculum learning (progressive difficulty)
- Specialized adapters per task type
- Continuous regression testing after each training run
- RL with LSP diagnostic feedback as reward signal

---

## Dependencies

```
Phase 12 (Server) ──────┬──→ Phase 13 (Evaluation)
                         │          │
Phase 14 (Data Infra) ──┼──────────┤
                         │          │
                         │          ├──→ Phase 15 (General Tune)
                         │          │          │
                         │          │          ├──→ Phase 16 (Tool Calling Tune)
                         │          │          │          │
                         │          │          │          ├──→ Phase 17 (Advanced)
```

Phases 12 and 14 can be developed in parallel.

## Implementation Approach

- New package: `src/punie/training/` (like `src/punie/perf/`, `src/punie/local/`)
- `mlx-lm` and `datasets` as regular dependencies in pyproject.toml
- Server/training launched as subprocess for lifecycle management
- All data structures are frozen dataclasses
- All scoring/validation/filtering via pure functions
- Integration tests marked `@pytest.mark.slow` (require model + server)
- Raw downloads in `data/raw/`, filtered outputs in `data/filtered/`, hand-authored in `data/hand-authored/`
- Adapters in `adapters/` directory (gitignored — large binary files)
- Each pruning step produces a new directory + filter report for full traceability

## Verification

After each phase:
1. All existing 297+ tests still pass
2. All new tests pass
3. `uv run ruff check src/punie/training/` clean
4. `uv run ty check src/punie/training/` clean
5. Coverage stays above 80%
