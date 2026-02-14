# Training Data Scaling Spec - References

## Related Code

- `scripts/clone_popular_repos.py` — Clone 10 Python repositories
- `scripts/generate_repo_examples.py` — AST-based example generation
- `scripts/generate_html_examples.py` — HTML domain examples
- `scripts/merge_phase6_data.py` — Merge Phase 5 + repos → Phase 6
- `scripts/merge_phase7_data.py` — Merge Phase 6 + HTML → Phase 7

## Training Data

- `data/repos/` — 10 cloned Python repositories (2,941 files)
- `data/repos_examples/training_examples.jsonl` — 550 repo examples
- `data/html_examples/training_examples.jsonl` — 30 HTML examples
- `data/phase6_format/` — 794 examples (Python only)
- `data/phase7_format/` — 824 examples (Python + HTML)

## Trained Models

- `adapters_phase6/` — Phase 6 LoRA weights (130MB, Python only)
- `adapters_phase7/` — Phase 7 LoRA weights (130MB, Python + HTML)
- Base model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

## Benchmarking

- `benchmark_all_phases.log` — Complete 5-model comparison
- `test_phase5_model.py` — Discrimination test suite

## External Dependencies

- **mlx-lm** — Apple MLX LoRA training and inference
- **ast** — Python AST parsing for code analysis
- Base model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

## Related Specs

- Phase 17: Knowledge Distillation (established training pipeline)
- Phase 18: Model Fusion (fusion techniques for deployment)
- Phase 20: Inference Speed Optimization (will optimize Phase 7)

## Documentation

- `MODEL_PERFORMANCE_TRACKER.md` — Phases 6-7 results
- `PHASE6_RESULTS.md` → `docs/diary/phase6-results.md`
- `PHASE7_RESULTS.md` → `docs/diary/phase7-results.md`
- `OVERNIGHT_PROGRESS.md` → `docs/diary/overnight-progress.md`
