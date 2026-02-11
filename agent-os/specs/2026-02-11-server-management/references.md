# Server Management Spec - References

## Related Code

- `src/punie/agent/factory.py` — Agent creation patterns, `_create_local_model()`
- `src/punie/local/client.py` — `LocalClient` non-frozen dataclass pattern
- `src/punie/perf/` — Similar package structure for specialized functionality

## External Dependencies

- **mlx-lm** — Apple MLX LoRA training and inference
  - `mlx_lm.server` — OpenAI-compatible API server
  - `mlx_lm.lora` — LoRA fine-tuning CLI
- **httpx** — Async HTTP client for health checks
- **psutil** — Optional process memory tracking

## Related Specs

- Phase 13: Evaluation Harness (depends on Phase 12)
- Phase 14: Training Data Infrastructure (depends on Phase 12)

## Documentation

- `docs/research/local-model-training-plan.md` — Full training infrastructure plan
- `agent-os/product/roadmap.md` — Project roadmap
