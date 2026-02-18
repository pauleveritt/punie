# Phase 33 References

## Data Sources

| Path | Description | Count |
|------|-------------|-------|
| `data/phase28_merged/train.jsonl` | Foundation training data (Phase 22-27) | 1019 |
| `data/phase28_merged/valid.jsonl` | Foundation validation data | 107 |
| `data/phase32_domain_tools/domain_tool_examples.jsonl` | New domain tool examples | ~150 |
| `data/phase33_merged/train.jsonl` | Final merged train set | ~1154 |
| `data/phase33_merged/valid.jsonl` | Final merged valid set | ~122 |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_phase32_domain_tool_examples.py` | Generate ~150 domain tool examples |
| `scripts/merge_phase33_data.py` | Merge all sources into phase33_merged |
| `scripts/generate_phase28_cross_tool_examples.py` | Reference: cross-tool example generation pattern |
| `scripts/merge_phase28_data.py` | Reference: merge script pattern |

## Training Infrastructure

| File | Purpose |
|------|---------|
| `src/punie/training/lora_config.py` | LoRAConfig frozen dataclass |
| `src/punie/training/train_runner.py` | `build_train_command()` + async runner |
| `src/punie/training/eval_suites.py` | Eval suite definitions |
| `src/punie/training/eval_prompts.py` | EvalPrompt + EvalSuite types |
| `configs/phase33_training.yaml` | Cosine LR schedule config for mlx_lm |

## Model Paths

| Path | Description |
|------|-------------|
| `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` | Base model (download from HuggingFace) |
| `adapters_phase33/` | LoRA adapter weights (training output) |
| `fused_model_qwen3_phase33_f16/` | Fused float16 model (intermediate) |
| `fused_model_qwen3_phase33_5bit/` | Final quantized production model |

## Predecessor Specs

- `agent-os/specs/2026-02-17-2100-domain-tools/` — Phase 32 domain tools spec
- `agent-os/specs/2026-02-16-phase28-server-client-separation/` — Phase 28 spec
- `agent-os/specs/2026-02-15-phase26-field-access-training/` — Phase 26 spec
