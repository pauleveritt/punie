# Model Fusion Spec - References

## Related Code

- `benchmark_phase5_vs_base.py` — Refactored to support N-model comparison
- `fused_model_f16/` — Float16 fused model (14.20 GB)
- `fused_model_8bit/` — 8-bit fused model (7.55 GB) ← PRODUCTION
- `.gitignore` — Added fused model directories

## Fusion Artifacts

- `benchmark_phase5c.log` — Complete 4-model benchmark results
- `adapters/` — Phase 5 LoRA weights (source for fusion)
- `fused_model/` — Deleted broken 4-bit fused model

## External Dependencies

- **mlx-lm** — Apple MLX model fusion and conversion
  - `mlx_lm.fuse` — Merge LoRA adapter into base model
  - `mlx_lm.convert` — Quantization and format conversion
- Base model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

## Related Specs

- Phase 17: Knowledge Distillation (created the adapters being fused)
- Phase 19: Training Data Scaling (uses fusion insights for Phase 6-7)
- Phase 20: Inference Speed Optimization (will fuse Phase 7 adapter)

## Documentation

- `MODEL_PERFORMANCE_TRACKER.md` — Phase 5c section with full results
- `docs/research/holy-grail-tools-domain.md` — Speedup techniques explored
