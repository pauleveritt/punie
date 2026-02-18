# Phase 40 References

## Model

| Model | Description |
|-------|-------------|
| `mlx-community/Qwen3-8B-4bit` | Base model for Phase 40 (HuggingFace MLX Community) |
| `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` | Phase 33b base model (for tokenizer cross-check) |

## Training Data (unchanged from Phase 33b)

| Path | Description | Count |
|------|-------------|-------|
| `data/phase33_merged/train.jsonl` | Training set | 1,159 |
| `data/phase33_merged/valid.jsonl` | Validation set | 123 |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/phase40_tokenizer_check.py` | Preflight: verify Qwen3-8B special token IDs |
| `scripts/run_phase40_8b_pipeline.sh` | Full train → fuse → quantize → eval pipeline |
| `scripts/run_phase33b_overnight.sh` | Template this was adapted from |
| `scripts/run_phase33_direct_eval.py` | Eval script (reused, model ID fix applied) |

## Output Paths

| Path | Description |
|------|-------------|
| `adapters_phase40_8b/` | LoRA adapter weights |
| `fused_model_qwen3_phase40_8b_f16/` | Fused float16 model (intermediate, deleted after quantize) |
| `fused_model_qwen3_phase40_8b_5bit/` | Final 5-bit quantized production model (~6 GB) |
| `logs/phase40_8b_training.log` | Full training log |

## Research Context

| File | Relevance |
|------|-----------|
| `docs/research/minimum-model-requirements.md` | Phase 25 failure analysis (7B tokenizer mismatch) |
| `docs/research/knowledge-distillation-update.md` | 7B memorization lessons |
| `docs/research/phase40-8b-results.md` | Results doc (created after eval run) |

## Predecessor Specs

- `agent-os/specs/2026-02-17-2300-full-retrain/` — Phase 33b spec (direct predecessor)
- `agent-os/specs/2026-02-14-phase25-7b-experiment/` — Phase 25 failure analysis
- `agent-os/specs/2026-02-17-2100-domain-tools/` — Phase 32 domain tools spec

## Training Infrastructure (unchanged)

| File | Purpose |
|------|---------|
| `src/punie/agent/prompt_utils.py` | `format_prompt()` — must use for all prompt formatting |
| `src/punie/training/checks.py` | Pipeline validation utilities |
| `src/punie/training/lora_config.py` | LoRAConfig frozen dataclass |
