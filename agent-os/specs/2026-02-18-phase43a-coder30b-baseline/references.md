# Phase 43a References

## Model

| Model | Description |
|-------|-------------|
| `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` | Base model for Phase 43a (same as Phase 33b) |

## Training Data (unchanged from Phase 33b)

| Path | Description | Count |
|------|-------------|-------|
| `data/phase33_merged/train.jsonl` | Training set | 1,159 |
| `data/phase33_merged/valid.jsonl` | Validation set | 123 |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_phase43a_coder30b.sh` | Full train → fuse → quantize → eval pipeline |
| `scripts/run_phase33b_overnight.sh` | Template this was adapted from (Phase 33b) |
| `scripts/run_phase33_direct_eval.py` | 27-prompt eval script (reused, model-agnostic) |

## Output Paths

| Path | Description |
|------|-------------|
| `adapters_phase43a/` | LoRA adapter weights |
| `fused_model_qwen3_phase43a_f16/` | Fused float16 model (intermediate, deleted after quantize) |
| `fused_model_qwen3_phase43a_coder30b_5bit/` | Final 5-bit quantized model (~20 GB) |
| `logs/phase43a_coder30b_training.log` | Full training log |

## Research Context

| File | Relevance |
|------|-----------|
| `docs/research/lora-degradation-and-model-variants.md` | Phase 43 research doc (MoE vs dense analysis) |
| `docs/research/phase40-8b-results.md` | Phase 40 8B failure — motivates staying on 30B |
| `docs/research/phase43a-coder30b-results.md` | Results doc (created before run, filled after) |
| `docs/research/minimum-model-requirements.md` | Updated after eval with Phase 43a scores |

## Predecessor Specs

- `agent-os/specs/2026-02-17-2300-full-retrain/` — Phase 33b spec (direct predecessor)
- `agent-os/specs/2026-02-18-phase40-smaller-model-experiment/` — Phase 40 8B failure
- `agent-os/specs/2026-02-18-phase42-toad-stabilization/` — Phase 42 (parallel to Phase 43)

## Training Infrastructure (unchanged)

| File | Purpose |
|------|---------|
| `src/punie/agent/prompt_utils.py` | `format_prompt()` — must use for all prompt formatting |
| `src/punie/training/checks.py` | Pipeline validation utilities |
| `src/punie/training/lora_config.py` | LoRAConfig frozen dataclass |
