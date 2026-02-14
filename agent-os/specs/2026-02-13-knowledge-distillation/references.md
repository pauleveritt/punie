# Knowledge Distillation Spec - References

## Related Code

- `src/punie/agent/factory.py` — Fixed stop_sequences key (line 241)
- `tests/test_agent_config.py` — Updated test assertions for stop_sequences
- `scripts/generate_training_data.py` — Original POC examples generator
- `scripts/convert_training_data.py` — Format converter with tool-call fix
- `scripts/generate_domain_examples.py` — Domain + direct-answer examples

## Training Data

- `data/hand_authored/` — Original 30 hand-authored examples
- `data/domain_examples.jsonl` — 21 domain + 50 direct-answer examples
- `data/mlx_format/train.jsonl` — 219 training examples
- `data/mlx_format/valid.jsonl` — 25 validation examples

## Trained Models

- `adapters/` — Phase 5 LoRA weights (44MB safetensors)
- Base model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

## External Dependencies

- **mlx-lm** — Apple MLX LoRA training and inference
  - `mlx_lm.lora` — LoRA fine-tuning CLI
  - `mlx_lm.server` — OpenAI-compatible API server
- **pydantic-ai-slim** — Agent framework with stop_sequences support

## Related Specs

- Phase 18: Model Fusion Optimization (depends on Phase 17 adapters)
- Phase 19: Training Data Scaling (builds on Phase 17 pipeline)

## Documentation

- `MODEL_PERFORMANCE_TRACKER.md` — Phase 0-5 results and benchmarks
- `docs/research/phase-19-public-datasets.md` — Public dataset research
- `docs/diary/phase6-results.md` — Subsequent training phases
